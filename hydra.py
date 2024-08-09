import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import tkinter.dnd as dnd
import vlc
import os
import json
import random
import time
import sys
import librosa
import pyloudnorm as pyln
import numpy as np

import threading
#from pyAudioAnalysis import audioBasicIO
#from pyAudioAnalysis import ShortTermFeatures

SUPPORTED_EXTENSIONS = (".mp3", ".wav", ".mp4", ".avi", ".mkv", ".flac", ".mov", ".wmv", ".ogg", ".m4a", ".m4v")
DEFAULT_VOLUME = 100
PROGRESS_UPDATE_INTERVAL = 100  # milliseconds

class MediaPlayer:

    def __init__(self, window):
        self.window = window
        self.window.title("Hydra Media Player")
        self.window.geometry("640x560")

        # Boolean Vars
        self.can_save_interval = True
        self.show_playlist = tk.BooleanVar(value=True)
        self.current_file = None
        self.show_subtitles = tk.BooleanVar(value=True)
        
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

        self.add_button = ttk.Button(playlist_buttons_frame, text="Add", command=self.add_to_playlist, takefocus=False)
        self.add_button.grid(row=0, column=0, padx=10)

        self.remove_button = ttk.Button(playlist_buttons_frame,text="Remove",command=self.remove_song, takefocus=False)
        self.remove_button.grid(row=0, column=1, padx=10)

        # Create listbox for playlists
        self.collections_listbox = tk.Listbox(self.collections_frame, width=50)
        self.collections_listbox.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        self.collections_listbox.bind('<Double-1>', self.load_selected_playlist)

        # Create buttons
        collection_buttons_frame = ttk.Frame(self.collections_frame)
        collection_buttons_frame.pack(pady=10)

        self.open_playlist_button = ttk.Button(collection_buttons_frame, text="Open", command=self.load_selected_playlist, takefocus=False)
        self.open_playlist_button.grid(row=0, column=0, padx=5)

        self.save_playlist_button = ttk.Button(collection_buttons_frame, text="Save", command=self.save_current_playlist_as, takefocus=False)
        self.save_playlist_button.grid(row=0, column=1, padx=5)

        # Load existing playlists
        self.load_playlists()

        # Add track label
        self.track_label = ttk.Label(self.window, text="No track playing", relief=tk.SUNKEN)
        self.track_label.pack(fill=tk.X, pady=5)

        # Add time label
        self.time_label = ttk.Label(self.window, text="00:00 / 00:00")
        self.time_label.pack(pady=5)

        # Add progress bar
        self.progress = ttk.Progressbar(self.window, orient=tk.HORIZONTAL, length=600, mode='determinate')
        self.progress.bind("<Button-1>", self.seek)
        self.progress.pack(pady=10)

        # Create button controls
        controls_frame = ttk.Frame(self.window)
        controls_frame.pack()

        self.play_pause_button = ttk.Button(controls_frame, text="Play", command=self.toggle_play_pause, takefocus=False)
        self.play_pause_button.grid(row=0, column=0, padx=10)

        self.previous_button = ttk.Button(controls_frame, text="Previous", command=self.previous_song, takefocus=False)
        self.previous_button.grid(row=0, column=1, padx=10)

        self.next_button = ttk.Button(controls_frame, text="Next", command=self.next_song, takefocus=False)
        self.next_button.grid(row=0, column=2, padx=10)

        self.stop_button = ttk.Button(controls_frame, text="Stop", command=self.stop, takefocus=False)
        self.stop_button.grid(row=0, column=3, padx=10)

        self.volume_slider = tk.Scale(controls_frame, from_=0, to=100, orient=tk.HORIZONTAL, label='Volume', command=self.set_volume, takefocus=False)
        self.volume_slider.set(DEFAULT_VOLUME)
        self.volume_slider.grid(row=0, column=4, padx=10)

        # Create media settings
        media_settings_frame = ttk.Frame(self.window)
        media_settings_frame.pack()

        self.shuffle = tk.BooleanVar(media_settings_frame, False)
        self.shuffle_button = ttk.Checkbutton(media_settings_frame, text="Shuffle", variable=self.shuffle, command=self.toggle_shuffle, takefocus=False)
        self.shuffle_button.grid(row=0, column=0)

        self.repeat_one = tk.BooleanVar(media_settings_frame, False)
        self.repeat_one_button = ttk.Checkbutton(media_settings_frame, text="Repeat One", variable=self.repeat_one, command=self.toggle_repeat_one, takefocus=False)
        self.repeat_one_button.grid(row=0, column=1)

        self.repeat_all = tk.BooleanVar(media_settings_frame, False)
        self.repeat_all_button = ttk.Checkbutton(media_settings_frame, text="Repeat All", variable=self.repeat_all, command=self.toggle_repeat_one, takefocus=False)
        self.repeat_all_button.grid(row=0, column=2)

        self.fullscreen = tk.BooleanVar(media_settings_frame, False)
        self.fullscreen_button = ttk.Checkbutton(media_settings_frame, text="Fullscreen", variable=self.fullscreen, command=self.set_fullscreen, takefocus=False)
        self.fullscreen_button.grid(row=0, column=3)

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
        self.load_last_playlist()
        self.default_subtitle_track = self.media_player.video_get_spu()
        print(self.media_player.video_get_spu())

        # Initialize theme
        self.toggle_theme()

        self.window.focus_set()
        self.on_media_changed()

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
            self.track_label.config(text=os.path.basename(selected_song))
            self.window.after(PROGRESS_UPDATE_INTERVAL, self.update_progress_bar)

            # Go to video frame if playing video
            if selected_song.endswith((".mp4", ".avi", ".mkv", ".mov")):
                self.notebook.select(self.video_frame)
            else:
                self.notebook.select(self.playlist_frame)

            self.current_file = selected_song
            self.next_button.config(state='enabled')
        except IndexError as e:
            messagebox.showerror("Error", str(e))
        except FileNotFoundError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def pause(self):
        self.media_player.pause()
        self.window.after(PROGRESS_UPDATE_INTERVAL, self.update_progress_bar)
        self.save_current_playlist()

    def toggle_play_pause(self, event=None):
        if self.media_player.is_playing():
            self.pause()
        else:
            if self.media_player.get_time()>0:
                self.pause()
            else:
                self.play()
            self.window.after(PROGRESS_UPDATE_INTERVAL, self.update_progress_bar)
    
        self.window.focus_set()

    def play_selected_file(self, event):
        selected_indices = self.playlist.curselection()
        if selected_indices:
            self.playlist.activate(selected_indices[0])
            self.play()
        self.window.focus_set()

    def update_play_pause_button(self):
        if self.media_player.is_playing():
            self.play_pause_button.config(text="Pause")
        else:
            self.play_pause_button.config(text="Play")
    
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
                self.window.after(PROGRESS_UPDATE_INTERVAL, self.update_play_pause_button)
            else:
                raise IndexError("No next song available")

        except IndexError:
            self.stop()
            self.track_label.config(text="End of Playlist")
            # Optionally, you could disable the next button here
            self.next_button.config(state='disabled')

        except Exception as e:
            print(f"Error in next_song: {e}")
            self.stop()
        self.window.focus_set()

    def song_finished(self, event):
        self.window.after(0,self.next_song) # call next_song on tkinter's main thread to prevent crashes
    
    def set_volume(self, volume):
        self.media_player.audio_set_volume(int(volume))

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
        self.window.bind_all("<space>", self.toggle_play_pause)
        self.window.bind_all("<Left>", self.previous_song)
        self.window.bind_all("<Right>", self.next_song)
        self.window.bind_all("<Shift-Up>", self.increase_volume)
        self.window.bind_all("<Shift-Down>", self.decrease_volume)
        self.window.bind_all("<Control-o>", self.add_to_playlist)
        self.window.bind_all("<Delete>", self.remove_song)
        self.window.bind_all("<Control-s>", self.save_playlist)
        self.window.bind_all("<Control-l>", self.load_playlist)
        self.window.bind_all("<f>", self.toggle_fullscreen)
        self.window.bind_all("<c>", self.toggle_subtitles)

        # Bind playlist shortcuts
        self.playlist.bind('<Double-1>', self.play_selected_file)
        self.playlist.bind('<Button-1>', self.drag_start)
        self.playlist.bind('<B1-Motion>', self.drag_motion)
        self.playlist.bind('<ButtonRelease-1>', self.drag_end)

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
                self.save_current_playlist()
                self.can_save_interval = False;
                self.window.after(2000, self.reset_interval)
            #self.window.after(1000,self.save_current_playlist)

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
        else:
            for file_path in file_paths:
                self.playlist.insert(tk.END, file_path)

    def remove_song(self, event=None):
        selected_index = self.playlist.curselection()[0]
        self.playlist.delete(selected_index)

    def save_playlist(self):
        playlist = self.playlist.get(0, tk.END)
        if playlist:
            file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
            if file_path:
                with open(file_path, 'w') as f:
                    json.dump(playlist, f)
                messagebox.showinfo("Success", "Playlist saved successfully")
        else:
            messagebox.showerror("Error", "No songs in the playlist")

    def load_playlist(self, file_path = None):
        if file_path == None:
            file_path = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        
        if file_path:
            with open(file_path, 'r') as f:
                playlist = json.load(f)
            self.playlist.delete(0, tk.END)
            for song in playlist:
                self.playlist.insert(tk.END, song)
            messagebox.showinfo("Success", "Playlist loaded successfully")

    def create_playlist_from_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            playlist = []
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if file.endswith(SUPPORTED_EXTENSIONS):
                        self.playlist.insert(tk.END, os.path.join(root, file))
            #messagebox.showinfo("Playlist Created", f"Playlist created with {len(playlist)} files")

    def on_closing(self):
        self.save_current_playlist()
        self.window.destroy()


    def on_media_changed(self, event=None):
        print("Media changed, updating tracks")
        self.window.after(2000, self.update_subtitle_tracks_menu)
        self.window.after(2000, self.update_audio_tracks_menu)
        
    def save_current_playlist(self):
        try:
            last_playlist = {
                "playlist": list(self.playlist.get(0, tk.END)),
                "file": self.current_file,
                "index": self.playlist.curselection()[0],
                "position": self.media_player.get_time() if self.current_file else 0
            }
            try:
                with open("last_playlist.json", 'w') as f:
                    json.dump(last_playlist, f)
                    print(f"Current Playlist saved.")
            except IOError as e:
                print(f"Error saving playlist: {e}")
        except IndexError:
            print("No playlist to save")
     
    def load_last_playlist(self):
        if os.path.exists("last_playlist.json"):
            try:
                with open("last_playlist.json", 'r') as f:
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
                        

                    # Start playing, then immediately pause to get around vlc's timelag weirdness when loading last position...
                    volume = self.media_player.audio_get_volume()
                    self.set_volume(0) # mute volume so you don't hear the song playing (has to play in order to set the time...)
                    self.toggle_play_pause() # play the song
                    self.media_player.set_time(int(position)) #set the position to the saved position
                    self.update_progress_bar()
                    time.sleep(.5) # sleep for half a second to allow vlc to load and process, otherwise it just resets the time counter
                    self.toggle_play_pause() # pause again
                    self.set_volume(volume)
                    self.media_player.set_time(int(position)) # reset volume and position back to what they were

                    # Update UI
                    self.track_label.config(text=os.path.basename(self.current_file))

                else:
                    print("Last played file not found or no file was playing")

            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading playlist: {e}")
    
    def clear_playlist(self):
        self.playlist.delete(0, tk.END)
        self.track_label.config(text="Playlist Empty")
        self.update_progress_bar()

    def load_playlists(self):
        playlist_dir = "playlists"
        if not os.path.exists(playlist_dir):
            os.makedirs(playlist_dir)
        
        playlists = [f for f in os.listdir(playlist_dir) if f.endswith('.json')]
        self.collections_listbox.delete(0, tk.END)
        for playlist in playlists:
            self.collections_listbox.insert(tk.END, playlist[:-5])  # Remove .json extension

    def load_selected_playlist(self, event=None):
        selection = self.collections_listbox.curselection()
        if selection:
            playlist_name = self.collections_listbox.get(selection[0])
            file_path = os.path.join("playlists", f"{playlist_name}.json")
            self.load_playlist(file_path)
    
    def save_current_playlist_as(self):
        playlist_name = simpledialog.askstring("Save Playlist", "Enter playlist name:")
        if playlist_name:
            file_path = os.path.join("playlists", f"{playlist_name}.json")
            playlist = list(self.playlist.get(0, tk.END))
            with open(file_path, 'w') as f:
                json.dump(playlist, f)
            self.load_playlists()  # Refresh the collections list

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
    def toggle_shuffle(self):
        print("Shuffle:", self.shuffle.get())

    def toggle_repeat_one(self):
        if self.repeat_one.get():
            self.repeat_all.set(False)
        print("Repeat One:", self.repeat_one.get())

    def toggle_repeat_all(self):
        if self.repeat_all.get():
            self.repeat_one.set(False)
        print("Repeat all:", self.repeat_all.get())

    def set_fullscreen(self, event=None):
        time_spot = self.media_player.get_time()
        self.stop()
        if self.fullscreen.get():
            self.detach_video()
            self.video_window.attributes('-fullscreen', True)
        else:
            self.video_window.attributes('-fullscreen', False)
            self.embed_video()
            self.video_canvas.pack(expand=True, fill='both')
        self.window.update()
        self.media_player.play()
        self.media_player.set_time(time_spot)
        self.window.after(PROGRESS_UPDATE_INTERVAL, self.update_progress_bar)
        print("Fullscreen:", self.fullscreen.get())

    def toggle_fullscreen(self, event=None):
        self.fullscreen.set(not self.fullscreen.get())
        self.set_fullscreen()

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
            self.media_player.video_set_spu(self.default_subtitle_track)
        else:
            self.show_subtitles.set(False)
            self.media_player.video_set_spu(-1)
        print("New Track:",self.media_player.video_get_spu(), "Show Subtitles:", self.show_subtitles.get())

    def update_subtitle_tracks_menu(self):
        self.subtitle_tracks_menu.delete(0, 'end')
        
        tracks = self.media_player.video_get_spu_description()
        if not tracks:
            self.subtitle_tracks_menu.add_command(label="No subtitles available", state='disabled')
        else:
            self.subtitle_tracks_menu.add_command(label="Disable subtitles", command=lambda: self.media_player.video_set_spu(-1))
            for i, track in enumerate(tracks):
                track_name = track.decode() if isinstance(track, bytes) else str(track)
                self.subtitle_tracks_menu.add_command(
                    label=track_name,
                    command=lambda id=track[0]: self.set_subtitle_track(id,i)
                )
    
    def update_audio_tracks_menu(self):
        self.audio_tracks_menu.delete(0, 'end')
        
        tracks = self.media_player.audio_get_track_description()
        if not tracks:
            self.audio_tracks_menu.add_command(label="No audio tracks available", state='disabled')
        else:
            for i, track in enumerate(tracks):
                track_name = track.decode() if isinstance(track, bytes) else str(track)
                self.audio_tracks_menu.add_command(
                    label=track_name,
                    command=lambda id=track[0]: self.set_audio_track(id,i)
                )

    def set_audio_track(self, track_id, index=1):
        self.media_player.audio_set_track(track_id)
        track_name = self.media_player.audio_get_track_description()[index][1].decode()
        print(f"Switched to audio track: {track_name}")

    def set_subtitle_track(self, track_id, index=1):
        self.media_player.video_set_spu(track_id)
        self.show_subtitles.set(True)
        self.default_subtitle_track = track_id
        if track_id == -1:
            print("Subtitles disabled")
        else:
            track_name = self.media_player.video_get_spu_description()[index][1].decode()
            print(f"Switched to subtitle track: {track_name}")
        
    # App Settings Methods
    def toggle_always_on_top(self):
        self.window.attributes('-topmost', self.always_on_top.get())

    def toggle_theme(self):
        self.style = ttk.Style()
        if self.dark_mode.get():
            self.style.theme_use('clam')
            self.window.configure(bg='#2E2E2E')
            self.style.configure('.', background='#2E2E2E', foreground='white')
            self.style.configure('TButton', background='#4D4D4D', foreground='white')
            self.style.map('TButton', background=[('active', '#6E6E6E')])
            self.style.configure('TFrame', background='#2E2E2E')
            self.playlist.configure(bg='#4D4D4D', fg='white', selectbackground='#6E6E6E', selectforeground='white')
            self.volume_slider.configure(bg='#2E2E2E', fg='white', troughcolor='#4D4D4D')
            self.style.map('TCheckbutton',
                       background=[('active', '#4D4D4D')],
                       foreground=[('active', 'white')])
        else:
            self.style.theme_use('default')
            self.window.configure(bg='#f7f7f7')
            self.style.configure('.', background='white', foreground='black')
            self.style.configure('TButton', background='#e1e1e1', foreground='black')
            self.style.map('TButton', background=[('active', '#d1d1d1')])
            self.style.configure('TFrame', background='#f7f7f7')
            self.playlist.configure(bg='white', fg='black', selectbackground='#D3D3D3', selectforeground='black')
            self.volume_slider.configure(bg='#f7f7f7', fg='black', troughcolor='#e1e1e1')
            self.style.map('TCheckbutton',
                       background=[('active', '#e1e1e1')],
                       foreground=[('active', 'black')])
            
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
        Left Arrow: Previous Track
        Right Arrow: Next Track
        Shift + Up Arrow: Volume Up
        Shift + Down Arrow: Volume Down
        Control + O: Add to Playlist
        Delete: Remove From Playlist
        Control + S: Save Playlist
        Control + L: Open Playlist
        F: Toggle Fullscreen
        C: Toggle Subtitles
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
        menubar = tk.Menu(self.window)
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
        options_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Options", menu=options_menu)
        options_menu.add_checkbutton(label="Shuffle", variable=self.shuffle, command=self.toggle_shuffle)
        options_menu.add_checkbutton(label="Repeat One", variable=self.repeat_one, command=self.toggle_repeat_one)
        options_menu.add_checkbutton(label="Repeat All", variable=self.repeat_all, command=self.toggle_repeat_all)
        options_menu.add_separator()
        options_menu.add_command(label="Toggle Fullscreen", command=self.toggle_fullscreen)
        #options_menu.add_checkbutton(label="Show Playlist", variable=self.show_playlist, command=self.toggle_playlist)
        options_menu.add_separator()
        options_menu.add_checkbutton(label="Always On Top", variable=self.always_on_top, command=self.toggle_always_on_top)
        options_menu.add_checkbutton(label="Dark Mode", variable=self.dark_mode, command=self.toggle_theme)

        # Tools Menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Media Information", command=self.show_media_info)
        tools_menu.add_command(label="Select Audio Device", command=self.select_audio_device)
        tools_menu.add_command(label="Show Equalizer", command=self.show_equalizer)
        tools_menu.add_command(label="Analyze Audio", command=self.perform_audio_analysis)

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

if __name__ == "__main__":
    window = tk.Tk()
    player = MediaPlayer(window)
    window.protocol("WM_DELETE_WINDOW", player.on_closing)
    window.mainloop()