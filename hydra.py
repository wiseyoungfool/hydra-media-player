import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import vlc
import os
import json
import random
import time

SUPPORTED_EXTENSIONS = (".mp3", ".wav", ".mp4", ".avi", ".mkv", ".flac", ".mov", ".wmv", ".ogg", ".m4a", ".m4v")
DEFAULT_VOLUME = 100
PROGRESS_UPDATE_INTERVAL = 100  # milliseconds

class MediaPlayer:

    def __init__(self, window):
        self.window = window
        self.window.title("Hydra Media Player")
        self.window.geometry("640x480")

        # Bind keyboard shortcuts
        self.window.bind("<space>", self.toggle_play_pause)
        self.window.bind("<Left>", self.previous_song)
        self.window.bind("<Right>", self.next_song)
        self.window.bind("<Up>", self.increase_volume)
        self.window.bind("<Down>", self.decrease_volume)
        self.window.bind("<Control-o>", self.add_to_playlist)
        self.window.bind("<Delete>", self.remove_song)
        self.window.bind("<Control-s>", self.save_playlist)
        self.window.bind("<Control-l>", self.load_playlist)

        # Create settings controls
        settings_frame = ttk.Frame(self.window)
        settings_frame.pack()

        self.always_on_top = tk.BooleanVar(settings_frame, False)
        self.always_on_top_button = ttk.Checkbutton(settings_frame, text="Toggle Always on Top", variable=self.always_on_top, command=self.toggle_always_on_top)
        self.always_on_top_button.grid(row=0, column=0)

        self.dark_mode = tk.BooleanVar(settings_frame, False)
        self.toggle_dark_mode = ttk.Checkbutton(settings_frame, text="Dark Mode", variable=self.dark_mode, command=self.toggle_theme)
        self.toggle_dark_mode.grid(row=0, column=1)

        # Create Playlist
        self.playlist = tk.Listbox(self.window, width = 100)
        self.playlist.pack(pady=10)

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

        self.play_pause_button = ttk.Button(controls_frame, text="Play", command=self.toggle_play_pause)
        self.play_pause_button.grid(row=0, column=0, padx=10)

        self.previous_button = ttk.Button(controls_frame, text="Previous", command=self.previous_song)
        self.previous_button.grid(row=0, column=1, padx=10)

        self.next_button = ttk.Button(controls_frame, text="Next", command=self.next_song)
        self.next_button.grid(row=0, column=2, padx=10)

        self.stop_button = ttk.Button(controls_frame, text="Stop", command=self.stop)
        self.stop_button.grid(row=0, column=3, padx=10)

        self.volume_slider = tk.Scale(controls_frame, from_=0, to=100, orient=tk.HORIZONTAL, label='Volume', command=self.set_volume)
        self.volume_slider.set(DEFAULT_VOLUME)
        self.volume_slider.grid(row=0, column=4, padx=10)

        # Create playlist controls
        self.open_button = ttk.Button(controls_frame, text="Open", command=self.add_to_playlist)
        self.open_button.grid(row=1, column=0, pady=10)

        self.remove_button = ttk.Button(controls_frame,text="Remove",command=self.remove_song)
        self.remove_button.grid(row=1, column=1, pady=10)

        self.save_button = ttk.Button(controls_frame, text="Save Playlist", command=self.save_playlist)
        self.save_button.grid(row=1, column=2, pady=10)

        self.load_button = ttk.Button(controls_frame, text="Load Playlist", command=self.load_playlist)
        self.load_button.grid(row=1, column=3, pady=10)

        # Create media settings
        media_settings_frame = ttk.Frame(self.window)
        media_settings_frame.pack()

        self.shuffle = tk.BooleanVar(media_settings_frame, False)
        self.shuffle_button = ttk.Checkbutton(media_settings_frame, text="Shuffle", variable=self.shuffle, command=self.toggle_shuffle)
        self.shuffle_button.grid(row=0, column=0)

        self.repeat_one = tk.BooleanVar(media_settings_frame, False)
        self.repeat_one_button = ttk.Checkbutton(media_settings_frame, text="Repeat One", variable=self.repeat_one, command=self.toggle_repeat_one)
        self.repeat_one_button.grid(row=0, column=1)

        self.repeat_all = tk.BooleanVar(media_settings_frame, False)
        self.repeat_all_button = ttk.Checkbutton(media_settings_frame, text="Repeat All", variable=self.repeat_all, command=self.toggle_repeat_one)
        self.repeat_all_button.grid(row=0, column=2)

        self.fullscreen = tk.BooleanVar(media_settings_frame, False)
        self.fullscreen_button = ttk.Checkbutton(media_settings_frame, text="Fullscreen", variable=self.fullscreen, command=self.toggle_fullscreen)
        self.fullscreen_button.grid(row=0, column=3)

        # Create the vlc player instance
        self.player = vlc.Instance()
        self.media_player = self.player.media_player_new()

        # Set the end event
        end_event = vlc.EventType.MediaPlayerEndReached
        self.media_player.event_manager().event_attach(end_event, self.song_finished)

        # Bind close event to window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Load Last playlist
        self.current_file = None
        self.load_last_playlist()

        # Initialize theme
        self.toggle_theme()

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
            self.media_player.set_media(media)
            self.media_player.play()
            self.track_label.config(text=os.path.basename(selected_song))
            self.window.after(PROGRESS_UPDATE_INTERVAL, self.update_progress_bar)
            if selected_song.endswith((".mp4",".avi", ".mkv", ".mov")): # Set fullscreen for video
                self.media_player.video_set_fullscreen(self.fullscreen)
            self.current_file = selected_song
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


    def toggle_play_pause(self):
        if self.media_player.is_playing():
            self.pause()
        else:
            if self.media_player.get_time()>0:
                self.pause()
            else:
                self.play()
            self.window.after(PROGRESS_UPDATE_INTERVAL, self.update_progress_bar)

    def update_play_pause_button(self):
        if self.media_player.is_playing():
            self.play_pause_button.config(text="Pause")
        else:
            self.play_pause_button.config(text="Play")
    
    def stop(self):
        self.media_player.stop()
        self.play_pause_button.config(text="Play")
        self.progress['value']=0;


    def previous_song(self):
        try:
            current_index = self.playlist.curselection()[0]
            previous_index = (current_index - 1) % self.playlist.size()
            self.playlist.selection_clear(0, tk.END)
            self.playlist.activate(previous_index)
            self.playlist.selection_set(previous_index)
            self.play()
        except IndexError:
            messagebox.showerror("Error", "No more songs in the playlist.")
            

    def next_song(self, event=None):
        try:
            self.stop()
            current_index = self.playlist.curselection()[0]
            if self.shuffle.get():
                next_index = random.randint(0, self.playlist.size() - 1)
            elif self.repeat_one.get():
                next_index = current_index
            else:
                next_index = (current_index + 1) % self.playlist.size()
            self.playlist.selection_clear(0, tk.END)
            self.playlist.activate(next_index)
            self.playlist.selection_set(next_index)
            self.play()
            self.window.after(PROGRESS_UPDATE_INTERVAL,self.update_play_pause_button)
        except IndexError:
            self.stop()
            if self.repeat_all.get():
                self.playlist.selection_clear(0, tk.END)
                self.playlist.activate(0)
                self.playlist.selection_set(0)
                self.play()
            else:
                self.track_label.config(text="End of Playlist")
            #messagebox.showinfo("End of Playlist", "No more songs in the playlist.")
        except Exception as e:
            print(f"Error in next_song: {e}")
            self.stop()


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


    # Progress Bar Methods
    def seek(self, event):
        length = self.media_player.get_length() / 1000  # Length in seconds
        click_position = event.x / self.progress.winfo_width()  # Position as a fraction
        new_time = length * click_position  # New time in seconds
        self.media_player.set_time(int(new_time * 1000))  # Set new time in milliseconds
        self.update_progress_bar()  # Update the progress bar


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


    def remove_song(self):
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


    def load_playlist(self):
        file_path = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if file_path:
            with open(file_path, 'r') as f:
                playlist = json.load(f)
            self.playlist.delete(0, tk.END)
            for song in playlist:
                self.playlist.insert(tk.END, song)
            messagebox.showinfo("Success", "Playlist loaded successfully")

    def on_closing(self):
        self.save_current_playlist()
        self.window.destroy()

    def save_current_playlist(self):
        last_playlist = {
            "playlist": list(self.playlist.get(0, tk.END)),
            "file": self.current_file,
            "index": self.playlist.curselection()[0],
            "position": self.media_player.get_time() if self.current_file else 0
        }
        try:
            with open("last_playlist.json", 'w') as f:
                json.dump(last_playlist, f)
                print("Current Playlist saved.")
        except IOError as e:
            print(f"Error saving playlist: {e}")

        
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

    def toggle_fullscreen(self):
        self.media_player.video_set_fullscreen(self.fullscreen.get())
        print("Fullscreen:", self.fullscreen.get())

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



if __name__ == "__main__":
    window = tk.Tk()
    player = MediaPlayer(window)
    window.mainloop()