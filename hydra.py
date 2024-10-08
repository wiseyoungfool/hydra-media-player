import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import tkinter.dnd as dnd
from PIL import Image, ImageTk
import vlc
import os
import json
import random
import time
import sys
import librosa
import pyloudnorm as pyln
import numpy as np
import sounddevice as sd
import configparser
import threading
#from pyAudioAnalysis import audioBasicIO
#from pyAudioAnalysis import ShortTermFeatures

SUPPORTED_EXTENSIONS = (".mp3", ".wav", ".mp4", ".avi", ".mkv", ".flac", ".mov", ".wmv", ".ogg", ".m4a", ".m4v")
DEFAULT_VOLUME = 100
PROGRESS_UPDATE_INTERVAL = 100  # milliseconds
BUTTON_SIZE = 30
SMALL_BUTTON_SIZE = 20
LIGHT_BG = '#a5b7ae'
DARK_BG = '#121212'

class MediaPlayer:

    def __init__(self, window):
        self.window = window
        self.window.title("Hydra Media Player")
        self.window.geometry("1280x800")

        # Boolean Vars
        self.can_save_interval = True
        self.show_playlist = tk.BooleanVar(value=True)
        self.current_file = None
        self.current_playlist = None
        self.mute_audio = False
        self.current_volume = DEFAULT_VOLUME
        self.show_subtitles = tk.BooleanVar(value=True)
        self.audio_track=1
        self.subtitle_track=1

        self.shuffle = tk.BooleanVar(value=False)
        self.repeat_one = tk.BooleanVar(value=False)
        self.repeat_all = tk.BooleanVar(value=False)
        self.fullscreen = tk.BooleanVar(value=False)
        
        # Create settings controls
        settings_frame = ttk.Frame(self.window)
        #settings_frame.pack()

        self.always_on_top = tk.BooleanVar(settings_frame, False)
        self.always_on_top_button = ttk.Checkbutton(settings_frame, text="Toggle Always on Top", variable=self.always_on_top, command=self.toggle_always_on_top, takefocus=False)
        #self.always_on_top_button.grid(row=0, column=0)

        self.dark_mode = tk.BooleanVar(settings_frame, False)
        self.toggle_dark_mode = ttk.Checkbutton(settings_frame, text="Dark Mode", variable=self.dark_mode, command=self.toggle_theme, takefocus=False)
        #self.toggle_dark_mode.grid(row=0, column=1)

        # Create a notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(expand=True, fill='both')

        # Create frames switchable tabs
        self.playlist_frame = ttk.Frame(self.notebook)
        self.video_frame = ttk.Frame(self.notebook)
        self.analysis_frame = ttk.Frame(self.notebook)
        self.collections_frame = ttk.Frame(self.notebook)

        self.analysis_results_frame = ttk.Frame(self.analysis_frame)
        self.analysis_results_frame.pack(expand=True, fill='both', pady=10)
        
        # Add frames to notebook
        self.notebook.add(self.playlist_frame, text='Playlist')
        self.notebook.add(self.video_frame, text='Video')
        self.notebook.add(self.analysis_frame, text='Analysis')
        self.notebook.add(self.collections_frame, text='Collections')

        # Create video canvas
        self.video_canvas = tk.Canvas(self.video_frame, bg='black')
        self.video_canvas.pack(expand=True, fill='both')

        # Create a separate window for the video
        self.video_window = tk.Toplevel(self.window)
        self.video_window.title("Video")
        self.video_window.geometry("1280x720")
        #self.video_window.overrideredirect(True)
        self.video_window.attributes('-topmost', True)
        self.video_window.withdraw()  # Hide the window initially

        # Create a frame in the video window
        self.video_window_frame = tk.Frame(self.video_window, bg='black')
        self.video_window_frame.pack(expand=True, fill='both')

        # Create Playlist
        self.playlist = tk.Listbox(self.playlist_frame, width=50)
        self.playlist.pack(pady=10, padx=10, expand=True, fill=tk.BOTH)

        # Create playlist controls
        playlist_buttons_frame = ttk.Frame(self.playlist_frame)
        playlist_buttons_frame.pack(pady=10)

        self.add_button = ttk.Button(playlist_buttons_frame, text="Add File", command=self.add_to_playlist, takefocus=False)
        self.add_button.grid(row=0, column=0, padx=10)

        self.add_folder_button = ttk.Button(playlist_buttons_frame, text="Add Folder", command=self.create_playlist_from_folder, takefocus=False)
        self.add_folder_button.grid(row=0, column=1, padx=10)

        self.remove_button = ttk.Button(playlist_buttons_frame,text="Remove",command=self.remove_song, takefocus=False)
        self.remove_button.grid(row=0, column=2, padx=10)

        self.save_pl_button = ttk.Button(playlist_buttons_frame, text="Save Playlist", command=self.save_playlist, takefocus=False)
        self.save_pl_button.grid(row=0, column=3, padx=10)

        self.clear_button = ttk.Button(playlist_buttons_frame,text="Clear",command=self.clear_playlist, takefocus=False)
        self.clear_button.grid(row=0, column=4, padx=10)

        # Create listbox for playlists
        self.collections_listbox = tk.Listbox(self.collections_frame, width=50)
        self.collections_listbox.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        self.collections_listbox.bind('<Double-1>', self.load_selected_playlist)

        # Create buttons
        collection_buttons_frame = ttk.Frame(self.collections_frame)
        collection_buttons_frame.pack(pady=10)

        self.open_playlist_button = ttk.Button(collection_buttons_frame, text="Open", command=self.load_selected_playlist, takefocus=False)
        self.open_playlist_button.grid(row=0, column=0, padx=5)

        self.save_playlist_button = ttk.Button(collection_buttons_frame, text="Save", command=self.save_playlist, takefocus=False)
        self.save_playlist_button.grid(row=0, column=1, padx=5)

        self.remove_playlist_button = ttk.Button(collection_buttons_frame, text="Remove", command=self.remove_playlist, takefocus=False)
        self.remove_playlist_button.grid(row=0, column=2, padx=5)

        # Load existing playlists
        self.load_playlists()

        # Load and resize images
        self.play_icon = Image.open("images/play.png").resize((BUTTON_SIZE, BUTTON_SIZE))
        self.pause_icon = Image.open("images/pause.png").resize((BUTTON_SIZE, BUTTON_SIZE))
        self.next_icon = Image.open("images/next.png").resize((BUTTON_SIZE, BUTTON_SIZE))
        self.back_icon = Image.open("images/back.png").resize((BUTTON_SIZE, BUTTON_SIZE))
        self.ff_icon = Image.open("images/fast-forward.png").resize((BUTTON_SIZE, BUTTON_SIZE))
        self.rew_icon = Image.open("images/rewind.png").resize((BUTTON_SIZE, BUTTON_SIZE))
        self.stop_icon = Image.open("images/stop.png").resize((BUTTON_SIZE, BUTTON_SIZE))
        self.fullscreen_icon = Image.open("images/fullscreen.png").resize((BUTTON_SIZE, BUTTON_SIZE))
        self.shrink_icon = Image.open("images/minimize.png").resize((BUTTON_SIZE, BUTTON_SIZE))
        self.volume_icon = Image.open("images/volume.png").resize((BUTTON_SIZE, BUTTON_SIZE))
        self.mute_icon = Image.open("images/mute.png").resize((BUTTON_SIZE, BUTTON_SIZE))
        self.repeat_all_icon = Image.open("images/repeat.png").resize((SMALL_BUTTON_SIZE, SMALL_BUTTON_SIZE))
        self.repeat_once_icon = Image.open("images/repeat-once.png").resize((SMALL_BUTTON_SIZE, SMALL_BUTTON_SIZE))
        self.shuffle_icon = Image.open("images/shuffle.png").resize((SMALL_BUTTON_SIZE, SMALL_BUTTON_SIZE))

        # Convert to PhotoImage
        self.play_icon = ImageTk.PhotoImage(self.play_icon)
        self.pause_icon = ImageTk.PhotoImage(self.pause_icon)
        self.next_icon = ImageTk.PhotoImage(self.next_icon)
        self.back_icon = ImageTk.PhotoImage(self.back_icon)
        self.ff_icon = ImageTk.PhotoImage(self.ff_icon)
        self.rew_icon = ImageTk.PhotoImage(self.rew_icon)
        self.stop_icon = ImageTk.PhotoImage(self.stop_icon)
        self.fullscreen_icon = ImageTk.PhotoImage(self.fullscreen_icon)
        self.shrink_icon = ImageTk.PhotoImage(self.shrink_icon)
        self.volume_icon = ImageTk.PhotoImage(self.volume_icon)
        self.mute_icon = ImageTk.PhotoImage(self.mute_icon)
        self.repeat_all_icon = ImageTk.PhotoImage(self.repeat_all_icon)
        self.repeat_once_icon = ImageTk.PhotoImage(self.repeat_once_icon)
        self.shuffle_icon = ImageTk.PhotoImage(self.shuffle_icon)

        # Create a style
        self.style = ttk.Style()
        
        self.style.configure("Mute.TButton", background="#e1e1e1")
        self.style.configure("RepeatAll.TButton", background="#e1e1e1")
        self.style.configure("RepeatOne.TButton", background="#e1e1e1")
        self.style.configure("Shuffle.TButton", background="#e1e1e1")
        self.style.configure("Fullscreen.TButton", background="#e1e1e1")

        # Create button controls
        controls_frame = ttk.Frame(self.window)
        controls_frame.pack(fill=tk.X)

        # Media info frame
        media_info_frame = ttk.Frame(controls_frame)
        media_info_frame.pack(fill=tk.X)

        # Add track and time labels in the same row
        info_frame = ttk.Frame(media_info_frame)
        info_frame.pack(fill=tk.X)
        self.track_label = ttk.Label(info_frame, text="No track playing", anchor='w')
        self.track_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.time_label = ttk.Label(info_frame, text="00:00 / 00:00", anchor='e')
        self.time_label.pack(side=tk.RIGHT)

        # Add progress bar
        self.progress = ttk.Progressbar(media_info_frame, orient=tk.HORIZONTAL, length=600, mode='determinate')
        self.progress.bind("<Button-1>", self.seek)
        self.progress.pack(fill=tk.X, pady=(5, 10))

        # Media buttons frame
        media_buttons_frame = ttk.Frame(controls_frame)
        media_buttons_frame.pack(fill=tk.X, padx = 5)

        # Create buttons
        self.play_pause_button = ttk.Button(media_buttons_frame, image=self.play_icon, command=self.toggle_play_pause, takefocus=False)
        self.play_pause_button.pack(side=tk.LEFT, padx=2)

        self.previous_button = ttk.Button(media_buttons_frame, image=self.back_icon, command=self.previous_song, takefocus=False)
        self.previous_button.pack(side=tk.LEFT, padx=2)

        self.backward_button = ttk.Button(media_buttons_frame, image=self.rew_icon, command=self.skip_backward, takefocus=False)
        self.backward_button.pack(side=tk.LEFT, padx=2)

        self.forward_button = ttk.Button(media_buttons_frame, image=self.ff_icon, command=self.skip_forward, takefocus=False)
        self.forward_button.pack(side=tk.LEFT, padx=2)

        self.next_button = ttk.Button(media_buttons_frame, image=self.next_icon, command=self.next_song, takefocus=False)
        self.next_button.pack(side=tk.LEFT, padx=2)

        self.stop_button = ttk.Button(media_buttons_frame, image=self.stop_icon, command=self.stop, takefocus=False)
        self.stop_button.pack(side=tk.LEFT, padx=2)

        # Volume slider
        self.volume_slider = ttk.Scale(media_buttons_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.set_volume, takefocus=False)
        self.volume_slider.set(DEFAULT_VOLUME)
        self.volume_slider.pack(side=tk.RIGHT, padx=(10, 0), fill=tk.X, expand=False)
        self.volume_label = ttk.Label(media_buttons_frame, text='Volume: 100%', width = 12, anchor='w')
        self.volume_label.pack(side=tk.RIGHT, padx=5)

        self.mute_button = ttk.Button(media_buttons_frame, image=self.volume_icon, command=self.toggle_mute, takefocus=False, style="Mute.TButton")
        self.mute_button.pack(side=tk.RIGHT, padx=2)
        
        self.fullscreen_button = ttk.Button(media_buttons_frame, image=self.fullscreen_icon, command=self.toggle_fullscreen, takefocus=False, style="Fullscreen.TButton")
        self.fullscreen_button.pack(side=tk.RIGHT, padx=2)

        self.repeat_all_button = ttk.Button(media_buttons_frame, image=self.repeat_all_icon, command=self.toggle_repeat_all, takefocus=False, style="RepeatAll.TButton")
        self.repeat_all_button.pack(side=tk.RIGHT, padx=2)

        self.repeat_one_button = ttk.Button(media_buttons_frame, image=self.repeat_once_icon, command=self.toggle_repeat_one, takefocus=False, style="RepeatOne.TButton")
        self.repeat_one_button.pack(side=tk.RIGHT, padx=2)

        self.shuffle_button = ttk.Button(media_buttons_frame, image=self.shuffle_icon, command=self.toggle_shuffle, takefocus=False, style="Shuffle.TButton")
        self.shuffle_button.pack(side=tk.RIGHT, padx=2)

        # Media settings frame
        media_settings_frame = ttk.Frame(controls_frame)
        media_settings_frame.pack(fill=tk.X, pady=(10, 0))

        # Create media settings buttons
        self.shuffle = tk.BooleanVar(media_settings_frame, False)
        #self.shuffle_button = ttk.Checkbutton(media_settings_frame, text="Shuffle", variable=self.shuffle, command=self.toggle_shuffle, takefocus=False)
        #self.shuffle_button.pack(side=tk.RIGHT, padx=5)

        self.repeat_one = tk.BooleanVar(media_settings_frame, False)
        #self.repeat_one_button = ttk.Checkbutton(media_settings_frame, text="Repeat One", variable=self.repeat_one, command=self.toggle_repeat_one, takefocus=False)
        #self.repeat_one_button.pack(side=tk.RIGHT, padx=5)

        self.repeat_all = tk.BooleanVar(media_settings_frame, False)
        #self.repeat_all_button = ttk.Checkbutton(media_settings_frame, text="Repeat All", variable=self.repeat_all, command=self.toggle_repeat_all, takefocus=False)
        #self.repeat_all_button.pack(side=tk.RIGHT, padx=5)

        self.fullscreen = tk.BooleanVar(media_settings_frame, False)
        #self.fullscreen_button = ttk.Checkbutton(media_settings_frame, text="Fullscreen", variable=self.fullscreen, command=self.set_fullscreen, takefocus=False)
        #self.fullscreen_button.pack(side=tk.RIGHT, padx=5)

        #Analysis controls
        self.analyze_button = ttk.Button(self.analysis_frame, text="Analyze Audio", command=self.perform_audio_analysis, takefocus=False)
        self.analyze_button.pack(pady=10)

        # Create the vlc player instance
        self.player = vlc.Instance()
        self.media_player = self.player.media_player_new()
        self.embed_video()

        # Set the end event
        end_event = vlc.EventType.MediaPlayerEndReached
        self.media_player.event_manager().event_attach(end_event, self.song_finished)
        self.media_player.event_manager().event_attach(vlc.EventType.MediaPlayerMediaChanged, self.on_media_changed)

        # Create menu
        self.create_menu()

        # Bind events
        self.create_event_bindings()
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Load Last playlist
        self.load_last_used_playlist()
        self.subtitle_track = self.media_player.video_get_spu()
        self.audio_track = self.media_player.audio_get_track()
        print(self.media_player.video_get_spu())

        self.window.focus_set()
        self.on_media_changed()

        self.load_settings()

    # Control Methods
    def play(self):
        try:
            selected_song = self.playlist.get(tk.ACTIVE)
            self.playlist.activate(tk.ACTIVE)
            self.playlist.selection_set(tk.ACTIVE)
            if not selected_song:
                raise IndexError("No song selected")
            if not os.path.exists(selected_song):
                raise FileNotFoundError(f"File not found: {selected_song}")
            media = self.player.media_new(selected_song)
            media.parse()
            self.media_player.set_media(media)
            self.media_player.play()
            self.window.after(PROGRESS_UPDATE_INTERVAL, self.update_progress_bar)

            # Go to video frame if playing video
            if selected_song.endswith((".mp4", ".avi", ".mkv", ".mov")):
                self.notebook.select(self.video_frame)
            else:
                self.notebook.select(self.playlist_frame)

            self.current_file = selected_song
            self.next_button.config(state='enabled')
            self.update_media_label()
        except IndexError as e:
            messagebox.showerror("Error", str(e))
        except FileNotFoundError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def pause(self, save=True):
        self.media_player.pause()
        self.window.after(PROGRESS_UPDATE_INTERVAL, self.update_progress_bar)
        if save==True:
            self.save_playlist('last_playlist', autosave=True)
            self.save_playlist(self.current_playlist, autosave=True)

    def toggle_play_pause(self, event=None):
        if self.media_player.is_playing():
            self.pause()
        else:
            if self.media_player.get_time()>0:
                self.pause()
            else:
                self.play()
            self.window.after(PROGRESS_UPDATE_INTERVAL, self.update_progress_bar)

        self.update_play_pause_button()
        self.window.focus_set()

    def play_selected_file(self, event):
        selected_indices = self.playlist.curselection()
        if selected_indices:
            self.playlist.activate(selected_indices[0])
            self.play()
        self.window.focus_set()

    def update_play_pause_button(self):
        if self.media_player.is_playing():
            self.play_pause_button.config(text="Pause", image=self.pause_icon)
        else:
            self.play_pause_button.config(text="Play", image=self.play_icon)
    
    def stop(self):
        self.media_player.stop()
        self.play_pause_button.config(text="Play")
        self.progress['value']=0;
        self.window.focus_set()

    def previous_song(self, event=None):
        try:
            current_index = self.playlist.curselection()[0]
            previous_index = current_index - 1
            if previous_index < 0:
                previous_index = 0
            self.playlist.selection_clear(0, tk.END)
            self.playlist.activate(previous_index)
            self.playlist.selection_set(previous_index)
            self.play()
        except IndexError:
            messagebox.showerror("Error", "No more songs in the playlist.")
        self.window.focus_set()
            
    def next_song(self, event=None):
        try:
            current_index = self.playlist.curselection()[0]
            next_index = None

            if self.shuffle.get():
                next_index = random.randint(0, self.playlist.size() - 1)
            elif self.repeat_one.get():
                next_index = current_index
            else:
                next_index = current_index + 1
                if next_index >= self.playlist.size():
                    if self.repeat_all.get():
                        next_index = 0
                    else:
                        raise IndexError("End of playlist")

            if next_index is not None:
                self.playlist.selection_clear(0, tk.END)
                self.playlist.activate(next_index)
                self.playlist.selection_set(next_index)
                self.stop()
                self.play()
                self.on_media_changed()
                self.window.after(PROGRESS_UPDATE_INTERVAL, self.update_play_pause_button)
            else:
                raise IndexError("No next song available")

        except IndexError:
            self.stop()
            self.track_label.config(text="End of Playlist")
            self.next_button.config(state='disabled')

        except Exception as e:
            print(f"Error in next_song: {e}")
            self.stop()
        self.window.focus_set()

    def skip_forward(self, event=None):
        current_position = self.media_player.get_time();
        self.media_player.set_time(current_position + (10 * 1000))  # Skip ahead 10 seconds
        self.update_progress_bar()  # Update the progress bar

    def skip_backward(self, event=None):
        current_position = self.media_player.get_time();
        self.media_player.set_time(current_position - (10 * 1000))  # Rewind 10 seconds
        self.update_progress_bar()  # Update the progress bar

    def song_finished(self, event):
        self.window.after(0,self.next_song) # call next_song on tkinter's main thread to prevent crashes
    
    def set_volume(self, volume):
        vol = int(float(volume))
        self.media_player.audio_set_volume(vol)
        self.current_volume = vol
        self.volume_label.config(text=f"Volume: {vol}%")

    def increase_volume(self, event=None):
        current_volume = self.volume_slider.get()
        new_volume = min(100, current_volume + 5)
        self.volume_slider.set(new_volume)
        self.set_volume(new_volume)

    def decrease_volume(self, event=None):
        current_volume = self.volume_slider.get()
        new_volume = max(0, current_volume - 5)
        self.volume_slider.set(new_volume)
        self.set_volume(new_volume)

    def create_event_bindings(self):
        # Bind keyboard shortcuts
        self.window.bind("<space>", self.toggle_play_pause)
        self.window.bind_all("<Left>", self.skip_backward)
        self.window.bind_all("<Right>", self.skip_forward)
        self.window.bind_all("<Control-Left>", self.previous_song)
        self.window.bind_all("<Control-Right>", self.next_song)
        self.window.bind_all("<Control-Up>", self.increase_volume)
        self.window.bind_all("<Control-Down>", self.decrease_volume)
        self.window.bind("<Control-o>", self.add_to_playlist)
        self.window.bind("<Delete>", self.remove_song)
        self.window.bind("<Control-s>", self.save_playlist)
        self.window.bind("<Control-l>", self.load_playlist)
        self.window.bind("<f>", self.toggle_fullscreen)
        self.window.bind("<c>", self.toggle_subtitles)
        self.window.bind("<i>", self.print_info)
        self.window.bind("<m>", self.toggle_mute)
        self.window.bind("<r>", self.toggle_repeat_all)
        self.window.bind("<l>", self.toggle_repeat_one)
        self.video_canvas.bind('<Double-1>', self.toggle_fullscreen)
        self.video_window.bind("<Escape>", self.toggle_fullscreen)
        self.video_window.bind('<Double-1>', self.toggle_fullscreen)
        self.video_window.bind("<space>", self.toggle_play_pause)

        # Bind playlist shortcuts
        self.playlist.bind('<Double-1>', self.play_selected_file)
        self.playlist.bind('<Button-1>', self.drag_start)
        self.playlist.bind('<B1-Motion>', self.drag_motion)
        self.playlist.bind('<ButtonRelease-1>', self.drag_end)

    def print_info(self, event=None):
        print(f"Audio Track: {self.media_player.audio_get_track()}")
        print(f"Subtitle Track: {self.media_player.video_get_spu()}")
        print(f"Current File: {self.current_file}")
        print(f"Current Playlist: {self.current_playlist}")
        print(f"Default Sub Track: {self.subtitle_track}")

    # Progress Bar Methods
    def seek(self, event):
        length = self.media_player.get_length() / 1000  # Length in seconds
        click_position = event.x / self.progress.winfo_width()  # Position as a fraction
        new_time = length * click_position  # New time in seconds
        self.media_player.set_time(int(new_time * 1000))  # Set new time in milliseconds
        self.update_progress_bar()  # Update the progress bar

    def reset_interval(self):
        self.can_save_interval = True

    def update_progress_bar(self):
        length = self.media_player.get_length() / 1000  # Length in seconds
        current_time = self.media_player.get_time() / 1000  # Current time in seconds
        self.progress['maximum'] = length
        self.progress['value'] = current_time
        
        # Update time label
        current_time_str = self.format_time(current_time)
        total_time_str = self.format_time(length)
        self.time_label.config(text=f"{current_time_str} / {total_time_str}")

        self.update_play_pause_button()
        if round(current_time) % 10 == 0:
            if self.can_save_interval:
                self.save_playlist('last_playlist', autosave=True)
                self.save_playlist(self.current_playlist, autosave=True)
                self.can_save_interval = False;
                self.window.after(2000, self.reset_interval)

        if self.media_player.is_playing():
            self.window.after(PROGRESS_UPDATE_INTERVAL, self.update_progress_bar)  # Update every interval

    def format_time(self, seconds):
        minutes, seconds = divmod(int(seconds), 60)
        return f"{minutes:02d}:{seconds:02d}"


    # Playlist Methods
    def add_to_playlist(self):
        file_paths = filedialog.askopenfilenames(defaultextension=".*", filetypes=[("All Files", "*.*")])

        if not file_paths: # Add folder as playlist
            folder_path = filedialog.askdirectory()
            if folder_path:
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        if file.endswith(SUPPORTED_EXTENSIONS):
                            self.playlist.insert(tk.END, os.path.join(root, file))
                self.select_default_track()
        else:
            for file_path in file_paths:
                self.playlist.insert(tk.END, file_path)
                self.select_default_track()

    def remove_song(self, event=None):
        selected_index = self.playlist.curselection()[0]
        self.playlist.delete(selected_index)

    def remove_playlist(self, event=None):
        if messagebox.askyesno("Delete Playlist", "Are you sure you want to delete this playlist?"):
            selected_index = self.collections_listbox.curselection()[0]
            self.collections_listbox.delete(selected_index)

    def create_playlist_from_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            playlist = []
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if file.endswith(SUPPORTED_EXTENSIONS):
                        self.playlist.insert(tk.END, os.path.join(root, file))
            self.select_default_track()

    def on_closing(self):
        self.save_settings()
        if self.playlist.size()>0:
            self.save_playlist("last_playlist", autosave=True)
            self.save_playlist(self.current_playlist)
        self.window.destroy()
    
    def select_default_track(self):
        if not self.playlist.curselection():
            self.playlist.activate(tk.ACTIVE)
            self.playlist.selection_set(tk.ACTIVE)
            self.update_media_label()
            #self.update_progress_bar()

    def on_media_changed(self, event=None):
        print("Media changed, updating tracks")
        self.window.after(2000, self.update_subtitle_tracks_menu)
        self.window.after(2000, self.update_audio_tracks_menu)
        time.sleep(.5)
        self.set_audio_track(self.audio_track)
        self.set_subtitle_track(self.subtitle_track)
        
    def save_playlist(self, playlist_name=None, autosave=False):
        # Get or set playlist name
        if playlist_name==None and autosave==False:
            playlist_name = simpledialog.askstring("Save Playlist", "Enter playlist name:")
        elif playlist_name==None:
            playlist_name='last_playlist'

        # Save playlist
        if playlist_name:
            file_path = os.path.join("playlists", f"{playlist_name}.json")
            try:
                # Write the playlist metadata
                playlist = {
                    "playlist": list(self.playlist.get(0, tk.END)),
                    "file": self.current_file,
                    "index": self.playlist.curselection()[0],
                    "position": self.media_player.get_time() if self.current_file else 0,
                    "name": playlist_name,
                    "subtitle_track": self.media_player.video_get_spu(),
                    "audio_track": self.media_player.audio_get_track()
                }
                try:
                    # Save the playlist
                    with open(file_path, 'w') as f:
                        json.dump(playlist, f)
                        self.load_playlists()  # Refresh the collections list
                        print(f"Playlist saved: {playlist_name}")

                    # Save the name of the current playlist in seperate file
                    with open("last_used_playlist.json", 'w') as f:
                        json.dump({"last_playlist": self.current_playlist}, f)

                    #print(f"Current Playlist: {self.current_playlist}")
                    if playlist_name!=None and autosave==False:
                        print("Loading Playlist...")
                        self.load_playlist(playlist_name)
                        

                except IOError as e:
                    print(f"Error saving playlist: {e}")
            except IndexError:
                print("No playlist to save")
     
    def load_playlist(self, playlist_name=None):
        if playlist_name:
            file_path = os.path.join("playlists", f"{playlist_name}.json")
        else:
            file_path = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])

        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    saved_data = json.load(f)
                
                # Load playlist
                self.playlist.delete(0, tk.END)
                for song in saved_data.get("playlist", []):
                    self.playlist.insert(tk.END, song)
                
                # Load last played file and position
                self.current_file = saved_data.get("file")
                if self.current_file and os.path.exists(self.current_file):
                    media = self.player.media_new(self.current_file)
                    self.media_player.set_media(media)
                    position = saved_data.get("position", 0)
                    self.media_player.set_time(int(position))
                    index = saved_data.get("index")
                    self.playlist.selection_clear(0, tk.END)
                    if index is not None:
                        self.playlist.activate(index)
                        self.playlist.selection_set(index) 

                    # Update UI
                    self.current_playlist = playlist_name
                    print(f"Playlist Loaded: {playlist_name}")
                    print(f"Current Playlist: {self.current_playlist}")
                    self.update_media_label()

                    # Start playing, then immediately pause to get around vlc's timelag weirdness when loading last position...
                    volume = self.media_player.audio_get_volume()
                    self.set_volume(0) # mute volume so you don't hear the song playing (has to play in order to set the time...)
                    self.play() # play the song
                    self.media_player.set_time(int(position)) #set the position to the saved position
                    self.update_progress_bar()
                    time.sleep(.5) # sleep for half a second to allow vlc to load and process, otherwise it just resets the time counter
                    self.pause(save=False) # pause again
                    self.set_volume(volume)
                    self.media_player.set_time(int(position)) # reset volume and position back to what they were

                    self.set_audio_track(saved_data.get("audio_track"))
                    self.set_subtitle_track(saved_data.get("subtitle_track"))
                else:
                    print("Last played file not found or no file was playing")

            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading playlist: {e}")
    
    def clear_playlist(self):
        self.stop()
        self.playlist.delete(0, tk.END)
        self.track_label.config(text="Playlist Empty")
        self.current_playlist = None
        self.update_progress_bar()

    def update_media_label(self):
        if self.current_playlist == None:
            playlist_text = 'Unsaved Playlist'
        else:
            playlist_text = self.current_playlist
        
        if self.current_file:
            file_text = os.path.basename(self.current_file)
        else:
            file_text = "No file selected"
        
        self.track_label.config(text=f'{playlist_text} - {file_text}')

    def load_playlists(self):
        playlist_dir = "playlists"
        if not os.path.exists(playlist_dir):
            os.makedirs(playlist_dir)
        
        playlists = [f for f in os.listdir(playlist_dir) if f.endswith('.json')]
        self.collections_listbox.delete(0, tk.END)
        for playlist in playlists:
            if not playlist.endswith('last_playlist.json'):
                self.collections_listbox.insert(tk.END, playlist[:-5])  # Remove .json extension

    def load_selected_playlist(self, event=None):
        selection = self.collections_listbox.curselection()
        if selection:
            playlist_name = self.collections_listbox.get(selection[0])
            self.load_playlist(playlist_name)

    def load_last_used_playlist(self):
        last_playlist_file = "last_used_playlist.json"
        if os.path.exists(last_playlist_file):
            try:
                with open(last_playlist_file, 'r') as f:
                    data = json.load(f)
                    last_playlist_name = data.get("last_playlist")
                    if last_playlist_name:
                        self.load_playlist(last_playlist_name)
                        print('Last playlist found, loading last playlist')
                        return
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading last used playlist: {e}")
        
        # Fallback to loading "last_playlist" if no last used playlist is found
        self.load_playlist("last_playlist")
        print('Last playlist not found, backup loaded')


    # Drag and Drop Playlist methods
    def drag_start(self, event):
        # Get the dragged item's index
        item = self.playlist.nearest(event.y)
        self.dragged_item = item

    def drag_motion(self, event):
        # Move the dragged item
        item = self.playlist.nearest(event.y)
        if item != self.dragged_item:
            text = self.playlist.get(self.dragged_item)
            self.playlist.delete(self.dragged_item)
            self.playlist.insert(item, text)
            self.dragged_item = item

    def drag_end(self, event):
        # Reset the dragged item
        self.dragged_item = None


    # Media Settings Methods
    def toggle_mute(self, event=None):
        if self.mute_audio:
            self.mute_audio = False
            self.media_player.audio_set_volume(self.current_volume)
            self.volume_label.config(text=f"Volume: {self.current_volume}%")
            self.reset_button_style('Mute.TButton')
            self.mute_button.configure(image=self.volume_icon)
        else:
            self.mute_audio = True
            self.media_player.audio_set_volume(0)
            self.volume_label.config(text=f"Volume: Mute")
            self.style.configure("Mute.TButton", background="#00FF00")
            self.style.map('Mute.TButton', background=[('active', '#7fff7f')])
            self.mute_button.configure(image=self.mute_icon)
        print(f"Mute audio: {self.mute_audio}")
        self.save_settings()

    def toggle_shuffle(self, event=None):
        self.shuffle.set(not self.shuffle.get())
        self.update_shuffle_button()
        print("Shuffle:", self.shuffle.get())
        self.save_settings()

    def toggle_repeat_one(self, event=None):
        self.repeat_one.set(not self.repeat_one.get())
        self.update_repeat_one_button()
        print("Repeat One:", self.repeat_one.get())
        self.save_settings()

    def toggle_repeat_all(self, event=None):
        self.repeat_all.set(not self.repeat_all.get())
        self.update_repeat_all_button()
        print("Repeat all:", self.repeat_all.get())
        self.save_settings()

    def update_shuffle_button(self):
        if self.shuffle.get():
            self.style.configure("Shuffle.TButton", background="#00FF00")
            self.style.map('Shuffle.TButton', background=[('active', '#7fff7f')])
            self.options_menu.entryconfig(0, selectcolor='green')
        else:
            self.reset_button_style('Shuffle.TButton')
            self.options_menu.entryconfig(0, selectcolor='')

    def update_repeat_one_button(self):
        if self.repeat_one.get():
            self.style.configure("RepeatOne.TButton", background="#00FF00")
            self.style.map('RepeatOne.TButton', background=[('active', '#7fff7f')])
            self.options_menu.entryconfig(1, selectcolor='green')
        else:
            self.reset_button_style('RepeatOne.TButton')
            self.options_menu.entryconfig(1, selectcolor='')

    def update_repeat_all_button(self):
        if self.repeat_all.get():
            self.style.configure("RepeatAll.TButton", background="#00FF00")
            self.style.map('RepeatAll.TButton', background=[('active', '#7fff7f')])
            self.options_menu.entryconfig(2, selectcolor='green')
        else:
            self.reset_button_style('RepeatAll.TButton')
            self.options_menu.entryconfig(2, selectcolor='')
            
    def set_fullscreen(self, event=None):
        time_spot = self.media_player.get_time()
        is_playing = self.media_player.is_playing()
        subtitle_track = self.media_player.video_get_spu()
        audio_track = self.media_player.audio_get_track()
        self.stop()
        if self.fullscreen.get():
            self.detach_video()
            #self.fullscreen_button.config(background="#00FF00", image=self.shrink_icon)
            self.video_window.attributes('-fullscreen', True)
        else:
            self.video_window.attributes('-fullscreen', False)
            #self.fullscreen_button.config(background="#e1e1e1", image=self.fullscreen_icon)
            self.embed_video()
            self.video_canvas.pack(expand=True, fill='both')
        self.window.update()
        self.media_player.play()
        self.media_player.set_time(time_spot)
        if not is_playing:
            self.window.after(500,self.pause)
        self.window.after(PROGRESS_UPDATE_INTERVAL, self.update_progress_bar)
        time.sleep(.5)
        self.set_audio_track(audio_track)
        self.set_subtitle_track(subtitle_track)
        print("Fullscreen:", self.fullscreen.get())

    def toggle_fullscreen(self, event=None):
        self.fullscreen.set(not self.fullscreen.get())
        self.set_fullscreen()
        #self.save_settings()

    def embed_video(self):
        if sys.platform.startswith('linux'):
            self.media_player.set_xwindow(self.video_canvas.winfo_id())
        elif sys.platform == "win32":
            self.media_player.set_hwnd(self.video_canvas.winfo_id())
        elif sys.platform == "darwin":
            self.media_player.set_nsobject(self.video_canvas.winfo_id())
        
        self.video_window.withdraw()

    def detach_video(self):
        if sys.platform.startswith('linux'):
            self.media_player.set_xwindow(self.video_window_frame.winfo_id())
        elif sys.platform == "win32":
            self.media_player.set_hwnd(self.video_window_frame.winfo_id())
        elif sys.platform == "darwin":
            self.media_player.set_nsobject(self.video_window_frame.winfo_id())
        
        self.video_canvas.pack_forget()
        self.video_window.deiconify()

    def toggle_subtitles(self, event=None):
        print("Old Track:", self.media_player.video_get_spu(),  "Show Subtitles:", self.show_subtitles.get())
        if self.media_player.video_get_spu() == -1:
            self.show_subtitles.set(True)
            self.media_player.video_set_spu(self.subtitle_track)
        else:
            self.show_subtitles.set(False)
            self.media_player.video_set_spu(-1)
        print("New Track:",self.media_player.video_get_spu(), "Show Subtitles:", self.show_subtitles.get())
        self.save_settings()

    def update_subtitle_tracks_menu(self):
        self.subtitle_tracks_menu.delete(0, 'end')
        
        tracks = self.media_player.video_get_spu_description()
        if not tracks:
            self.subtitle_tracks_menu.add_command(label="No subtitles available", state='disabled')
        else:
            #self.subtitle_tracks_menu.add_command(label="Disable subtitles", command=lambda: self.set_subtitle_track(-1))
            for track in tracks:
                track_id, track_name = track[0], track[1].decode() if isinstance(track[1], bytes) else str(track[1])
                self.subtitle_tracks_menu.add_command(
                    label=track_name,
                    command=lambda id=track_id, name=track_name: self.set_subtitle_track(id, name)
                )
    
    def update_audio_tracks_menu(self):
        self.audio_tracks_menu.delete(0, 'end')
        
        tracks = self.media_player.audio_get_track_description()
        if not tracks:
            self.audio_tracks_menu.add_command(label="No audio tracks available", state='disabled')
        else:
            for track in tracks:
                track_id, track_name = track[0], track[1].decode() if isinstance(track[1], bytes) else str(track[1])
                self.audio_tracks_menu.add_command(
                    label=track_name,
                    command=lambda id=track_id, name=track_name: self.set_audio_track(id,name)
                )

    def set_audio_track(self, track_id, track_name=None):
        self.media_player.audio_set_track(track_id)
        self.audio_track=track_id
        print(f"Switched to audio track: {track_name}")

    def set_subtitle_track(self, track_id, track_name=None):
        self.media_player.video_set_spu(track_id)
        self.show_subtitles.set(True)
        self.subtitle_track = track_id
        if track_id == -1:
            print("Subtitles disabled")
        else:
            print(f"Switched to subtitle track: {track_name}")
            
    # App Settings Methods
    def toggle_always_on_top(self):
        is_on_top = self.always_on_top.get()
        self.window.attributes('-topmost', is_on_top)
        self.video_window.attributes('-topmost', is_on_top)
        print(f"Always on top: {is_on_top}")
        self.save_settings()

    def reset_button_style(self, name):
        if self.dark_mode.get():
            self.style.configure(name, background='#333333', foreground='white', borderwidth=0, relief='flat')
            self.style.map(name, background=[('active', '#555555')])
        else:
            self.style.configure(name, background='#e1e1e1', foreground='black', borderwidth=0, relief='flat')
            self.style.map(name, background=[('active', '#d1d1d1')])

    def toggle_theme(self):
        if self.dark_mode.get():
            # Apply dark theme
            #self.style.theme_use('clam')
            self.style.theme_use('default')
            self.window.configure(bg=DARK_BG)
            self.style.configure('.', background=DARK_BG, foreground='white', font=('Helvetica', 10))
            self.style.configure('TButton', background='#333333', foreground='white', borderwidth=0, relief='flat')
            self.style.map('TButton', background=[('active', '#555555')])
            self.style.configure('TFrame', background=DARK_BG)
            self.style.configure('TNotebook', background=DARK_BG, foreground='white', borderwidth=0, highlightbackground=DARK_BG)
            self.style.configure('TNotebook.Tab', background='#1E1E1E', foreground='white', padding=[10, 5], borderwidth=0, highlightbackground=DARK_BG)
            self.style.map('TNotebook.Tab', background=[('selected', '#333333')], foreground=[('selected', 'white')])
            self.playlist.configure(bg='#333333', fg='white', selectbackground='#555555', selectforeground='white', highlightthickness=0)
            self.collections_listbox.configure(bg='#333333', fg='white', selectbackground='#555555', selectforeground='white', highlightthickness=0)
            self.style.configure('TScale',troughcolor='#333333', background = '#818181', highlightthickness=5)
            self.style.configure('TCheckbutton', background='#1E1E1E', foreground='white')
            self.style.map('TCheckbutton', background=[('active', '#333333')], foreground=[('active', 'white')])
            self.style.configure('TProgressbar', troughcolor='#333333', background='#00FF00', thickness=10)
            #self.progress.configure(style='TProgressbar', length=200, mode='determinate')

            self.style.configure("Mute.TButton", background="#333333")
            self.style.configure("RepeatAll.TButton", background="#333333")
            self.style.configure("RepeatOne.TButton", background="#333333")
            self.style.configure("Shuffle.TButton", background="#333333")
            self.style.configure("Fullscreen.TButton", background="#333333")
        else:
            # Apply light theme
            self.style.theme_use('default')
            self.window.configure(bg=LIGHT_BG)
            self.style.configure('.', background=LIGHT_BG, foreground='black', font=('Helvetica', 10))
            self.style.configure('TButton', background='#e1e1e1', foreground='black', borderwidth=0, relief='flat')
            self.style.map('TButton', background=[('active', '#d1d1d1')])
            self.style.configure('TFrame', background=LIGHT_BG)
            self.style.configure('TNotebook', background=LIGHT_BG, foreground='black', borderwidth=0, highlightbackground='#f7f7f7')
            self.style.configure('TNotebook.Tab', background='#e1e1e1', foreground='black', padding=[10, 5], borderwidth=0, highlightbackground='#f7f7f7')
            self.style.map('TNotebook.Tab', background=[('selected', '#f7f7f7')], foreground=[('selected', 'black')])
            self.playlist.configure(bg='white', fg='black', selectbackground='#D3D3D3', selectforeground='black', highlightthickness=0)
            self.collections_listbox.configure(bg='white', fg='black', selectbackground='#D3D3D3', selectforeground='black', highlightthickness=0)
            self.style.configure('TScale',troughcolor='#818181', background = '#f7f7f7', highlightthickness=5)
            self.style.configure('TCheckbutton', background='#f7f7f7', foreground='black')
            self.style.map('TCheckbutton', background=[('active', '#e1e1e1')], foreground=[('active', 'black')])
            self.style.configure('TProgressbar', troughcolor='#818181', background='#00FF00', thickness=10)
            #self.progress.configure(style='TProgressbar', length=200, mode='determinate')
            self.style.configure("Mute.TButton", background="#e1e1e1")
            self.style.configure("RepeatAll.TButton", background="#e1e1e1")
            self.style.configure("RepeatOne.TButton", background="#e1e1e1")
            self.style.configure("Shuffle.TButton", background="#e1e1e1")
            self.style.configure("Fullscreen.TButton", background="#e1e1e1")
        
        self.update_shuffle_button()
        self.update_repeat_one_button()
        self.update_repeat_all_button()

            
     # View Menu Methods

    def toggle_playlist(self):
        if self.show_playlist.get():
            self.playlist_frame.pack(side="right", fill="y")
        else:
            self.playlist_frame.pack_forget()

    def show_equalizer(self):
        equalizer_window = tk.Toplevel(self.window)
        equalizer_window.title("Equalizer")
        # Here you would add sliders for different frequency bands
        # This is a placeholder implementation
        tk.Label(equalizer_window, text="Equalizer not implemented yet").pack()


    # Tools Menu Methods
    def show_media_info(self):
        if self.current_file:
            media = self.media_player.get_media()
            info = f"Title: {media.get_meta(vlc.Meta.Title)}\n"
            info += f"Artist: {media.get_meta(vlc.Meta.Artist)}\n"
            info += f"Album: {media.get_meta(vlc.Meta.Album)}\n"
            info += f"Duration: {self.media_player.get_length() / 1000} seconds"
            messagebox.showinfo("Media Information", info)
        else:
            messagebox.showinfo("Media Information", "No media currently playing")

    def select_audio_device(self):
        devices = self.player.audio_output_device_enum()
        device_list = [device.description for device in devices]
        device = simpledialog.askstring("Select Audio Device", "Choose an audio device:", initialvalue=device_list[0])
        if device in device_list:
            self.media_player.audio_output_device_set(None, device)


    # Help Menu Methods
    def show_shortcuts(self):
        shortcuts = """
        Space: Play/Pause
        Left Arrow: Skip Behind
        Right Arrow: Skip Ahead
        Control + Left Arrow: Previous Track
        Control + Right Arrow: Next Track
        Control + Up Arrow: Volume Up
        Control + Down Arrow: Volume Down
        Control + O: Add to Playlist
        Delete: Remove From Playlist
        Control + S: Save Playlist
        Control + L: Open Playlist
        F: Toggle Fullscreen
        C: Toggle Subtitles
        M: Mute audio
        R: Repeat playlist
        L: Repeat track/file
        """
        messagebox.showinfo("Keyboard Shortcuts", shortcuts)

    def show_about(self):
        about_text = """
        Hydra Media Player
        Version 0.1
        
        Created by Brian Lynch
        
        A versatile media player built with Python and VLC.
        """
        messagebox.showinfo("About Hydra Media Player", about_text)
 
    def create_menu(self):
        menubar = tk.Menu(self.window, bg='#333333', fg='white', activebackground='#555555', activeforeground='white')
        self.window.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open File", command=self.add_to_playlist)
        file_menu.add_command(label="Create Playlist from Folder", command=self.create_playlist_from_folder)
        file_menu.add_command(label="Save Playlist", command=self.save_playlist)
        file_menu.add_command(label="Load Playlist", command=self.load_playlist)
        file_menu.add_separator()
        file_menu.add_command(label="Clear Playlist", command=self.clear_playlist)
        file_menu.add_command(label="Exit", command=self.on_closing)

        # Playback Menu
        playback_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Playback", menu=playback_menu)
        playback_menu.add_command(label="Play", command=self.play)
        playback_menu.add_command(label="Pause", command=self.pause)
        playback_menu.add_command(label="Stop", command=self.stop)
        playback_menu.add_command(label="Next", command=self.next_song)
        playback_menu.add_command(label="Previous", command=self.previous_song)
        playback_menu.add_separator()
        subtitle_menu = tk.Menu(playback_menu, tearoff=0)
        playback_menu.add_cascade(label="Subtitles", menu=subtitle_menu)
        subtitle_menu.add_checkbutton(label="Toggle Subtitles", variable=self.show_subtitles, state='active', command=self.toggle_subtitles)
        self.subtitle_tracks_menu = tk.Menu(subtitle_menu, tearoff=0)
        subtitle_menu.add_cascade(label="Select Subtitle Track", menu=self.subtitle_tracks_menu)
        self.subtitle_tracks_menu.add_command(label="No media loaded", state='disabled')
         # Add Audio menu
        audio_menu = tk.Menu(playback_menu, tearoff=0)
        playback_menu.add_cascade(label="Audio", menu=audio_menu)
        
        # Create a submenu for audio tracks
        self.audio_tracks_menu = tk.Menu(audio_menu, tearoff=0)
        audio_menu.add_cascade(label="Select Audio Track", menu=self.audio_tracks_menu)

        # Initialize with "No media loaded" or similar
        self.audio_tracks_menu.add_command(label="No media loaded", state='disabled')

        # Options Menu
        self.options_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Options", menu=self.options_menu)
        self.options_menu.add_checkbutton(label="Shuffle", command=self.toggle_shuffle)
        self.options_menu.add_checkbutton(label="Repeat One", command=self.toggle_repeat_one)
        self.options_menu.add_checkbutton(label="Repeat All", command=self.toggle_repeat_all)
        self.options_menu.add_separator()
        self.options_menu.add_command(label="Toggle Fullscreen", command=self.toggle_fullscreen)
        #self.options_menu.add_checkbutton(label="Show Playlist", variable=self.show_playlist, command=self.toggle_playlist)
        self.options_menu.add_separator()
        self.options_menu.add_checkbutton(label="Always On Top", variable=self.always_on_top, command=self.toggle_always_on_top)
        self.options_menu.add_checkbutton(label="Dark Mode", variable=self.dark_mode, command=self.toggle_theme)
        self.options_menu.add_separator()
        self.options_menu.add_command(label="Reset Settings", command=self.reset_settings)

        # Tools Menu
        self.tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=self.tools_menu)
        self.tools_menu.add_command(label="Media Information", command=self.show_media_info)
        self.tools_menu.add_command(label="Select Audio Device", command=self.select_audio_device)
        self.tools_menu.add_command(label="Show Equalizer", command=self.show_equalizer)
        self.tools_menu.add_command(label="Analyze Audio", command=self.perform_audio_analysis)

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts)
        help_menu.add_command(label="About", command=self.show_about)

    # Audio Analysis
    
    def perform_audio_analysis(self):
        if not self.current_file:
            messagebox.showinfo("Error", "No file is currently playing")
            return
        
        self.analyze_button.config(text="Analyzing...")
        threading.Thread(target=self._run_analysis, daemon=True).start()
        
    def _run_analysis(self):
        # Load the audio file
        y, sr = librosa.load(self.current_file)

        # Tempo
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        tempo = float(tempo)

        # Key
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_sum = np.sum(chroma, axis=1)
        key_index = np.argmax(chroma_sum)
        key_map = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        key = key_map[key_index]

        # LUFS
        meter = pyln.Meter(sr) # create BS.1770 meter
        loudness = meter.integrated_loudness(y)

        # RMS
        rms = librosa.feature.rms(y=y)[0].mean()

        # Frequency analysis
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0].mean()
        
        # Spectral Rolloff
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0].mean()

        # Update the UI in the main thread
        self.window.after(0, self.update_analysis_display, tempo, key, loudness, rms, spectral_centroid, spectral_rolloff)
    
    def update_analysis_display(self, tempo, key, loudness, rms, spectral_centroid, spectral_rolloff):
        self.analyze_button.config(text="Analyze Audio")
        
        # Clear previous content in the results frame
        for widget in self.analysis_results_frame.winfo_children():
            widget.destroy()

        # Create labels with analysis results
        ttk.Label(self.analysis_results_frame, text=f"Tempo: {float(tempo):.2f} BPM").pack()
        ttk.Label(self.analysis_results_frame, text=f"Estimated Key: {key}").pack()
        ttk.Label(self.analysis_results_frame, text=f"LUFS: {float(loudness):.2f}").pack()
        ttk.Label(self.analysis_results_frame, text=f"RMS: {float(rms):.4f}").pack()
        ttk.Label(self.analysis_results_frame, text=f"Spectral Centroid: {float(spectral_centroid):.2f} Hz").pack()
        ttk.Label(self.analysis_results_frame, text=f"Spectral Rolloff: {float(spectral_rolloff):.2f} Hz").pack()

        print("Audio Analysis Complete")

    def select_audio_device(self):
        devices = sd.query_devices()
        device_list = [f"{i}: {device['name']}" for i, device in enumerate(devices) if device['max_output_channels'] > 0]
        
        device_window = tk.Toplevel(self.window)
        device_window.title("Select Audio Device")
        device_window.geometry("300x400")
        
        listbox = tk.Listbox(device_window, width=50, height=20)
        listbox.pack(pady=10)
        
        for device in device_list:
            listbox.insert(tk.END, device)
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                device_id = int(device_list[selection[0]].split(":")[0])
                self.media_player.audio_output_device_set(None, devices[device_id]['name'].encode('utf-8'))
                messagebox.showinfo("Audio Device", f"Selected device: {devices[device_id]['name']}")
                device_window.destroy()
        
        select_button = ttk.Button(device_window, text="Select", command=on_select)
        select_button.pack(pady=10)

    # Settings
    def save_settings(self):
        config = configparser.ConfigParser()
        config['Settings'] = {
            'dark_mode': str(self.dark_mode.get()),
            'volume': str(self.current_volume),
            'always_on_top': str(self.always_on_top.get()),
            'show_subtitles': str(self.show_subtitles.get()),
            'shuffle': str(self.shuffle.get()),
            'repeat_one': str(self.repeat_one.get()),
            'repeat_all': str(self.repeat_all.get()),
            'window_width': str(window.winfo_width()),
            'window_height': str(window.winfo_height()),
            #'fullscreen': str(self.fullscreen.get())
        }
        
        with open('settings.ini', 'w') as configfile:
            config.write(configfile)

        print("Settings saved.")

    def load_settings(self):
        config = configparser.ConfigParser()
        config.read('settings.ini')
        
        if 'Settings' in config:
            # Load boolean settings
            self.dark_mode.set(config.getboolean('Settings', 'dark_mode', fallback=False))
            self.always_on_top.set(config.getboolean('Settings', 'always_on_top', fallback=False))
            self.show_subtitles.set(config.getboolean('Settings', 'show_subtitles', fallback=True))
            self.shuffle.set(config.getboolean('Settings', 'shuffle', fallback=False))
            self.repeat_one.set(config.getboolean('Settings', 'repeat_one', fallback=False))
            self.repeat_all.set(config.getboolean('Settings', 'repeat_all', fallback=False))
            width = config.getint('Settings', 'window_width', fallback=1280)
            height = config.getint('Settings', 'window_height', fallback=800)

            # Enforce minimum values
            if width < 660:
                width = 660
            if height < 480:
                height = 480

            self.window.geometry(f"{width}x{height}")

            #self.fullscreen.set(config.getboolean('Settings', 'fullscreen', fallback=False))
            
            # Load integer settings
            self.current_volume = config.getint('Settings', 'volume', fallback=DEFAULT_VOLUME)
            
            # Apply loaded settings
            self.set_volume(self.current_volume)
            self.volume_slider.set(self.current_volume)  # Update slider position
            self.toggle_always_on_top()
            #self.toggle_fullscreen()

        # Ensure theme is applied
        self.toggle_theme()

    def reset_settings(self):
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to default?"):
            os.remove('settings.ini')
            self.load_settings()
            self.save_settings() 


if __name__ == "__main__":
    window = tk.Tk()
    player = MediaPlayer(window)
    window.protocol("WM_DELETE_WINDOW", player.on_closing)
    window.mainloop()