import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import vlc
import os
import json

class MediaPlayer:

    def __init__(self, window):
        self.window = window
        self.window.title("Hydra Media Player")
        self.window.geometry("640x480")

        # Create settings controls
        settings_frame = ttk.Frame(self.window)
        settings_frame.pack()

        self.always_on_top = tk.BooleanVar(settings_frame, False)
        self.always_on_top_button = ttk.Checkbutton(settings_frame, text="Toggle Always on Top", variable=self.always_on_top, command=self.toggle_always_on_top)
        self.always_on_top_button.grid(row=0, column=0)

        self.dark_mode = tk.BooleanVar(settings_frame, False)
        self.toggle_dark_mode = ttk.Checkbutton(settings_frame, text="Dark Mode", variable=self.dark_mode, command=self.toggle_theme)
        self.toggle_dark_mode.grid(row=0, column=1)

        self.playlist = tk.Listbox(self.window, width = 100)
        self.playlist.pack(pady=10)

        # Add track label
        self.track_label = ttk.Label(self.window, text="No track playing", relief=tk.SUNKEN)
        self.track_label.pack(fill=tk.X, pady=5)

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
        self.volume_slider.set(70)
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

        # Create the vlc player instance
        self.player = vlc.Instance()
        self.media_player = self.player.media_player_new()

        # Set the end event
        end_event = vlc.EventType.MediaPlayerEndReached
        self.media_player.event_manager().event_attach(end_event, self.song_finished)

        # Bind close event to window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Open last playlist automatically
        if os.path.exists("last_playlist.json"):
            with open("last_playlist.json", 'r') as f:
                playlist = json.load(f)
            for song in playlist:
                self.playlist.insert(tk.END, song)

        # Initialize theme
        self.toggle_theme()

    # Control Methods
    def play(self):
        try:
            selected_song = self.playlist.get(tk.ACTIVE)
            media = self.player.media_new(selected_song)
            self.media_player.set_media(media)
            self.media_player.play()
            self.track_label.config(text=os.path.basename(selected_song))
            self.window.after(500, self.update_progress_bar)
        except IndexError:
            messagebox.showerror("Error", "No song selected")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")


    def pause(self):
        self.media_player.pause()
        self.window.after(500, self.update_progress_bar)


    def toggle_play_pause(self):
        if self.media_player.is_playing():
            self.pause()
            self.play_pause_button.config(text="Play")
        else:
            if self.media_player.get_time()>0:
                self.pause()
            else:
                self.play()
            self.play_pause_button.config(text="Pause")
            self.window.after(500, self.update_progress_bar)


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
            next_index = (current_index + 1) % self.playlist.size()
            self.playlist.selection_clear(0, tk.END)
            self.playlist.activate(next_index)
            self.playlist.selection_set(next_index)
            self.play()
        except IndexError:
            self.stop()
            #messagebox.showinfo("End of Playlist", "No more songs in the playlist.")
        except Exception as e:
            print(f"Error in next_song: {e}")
            self.stop()


    def song_finished(self, event):
        self.window.after(0,self.next_song) # call next_song on tkinter's main thread to prevent crashes
    

    def set_volume(self, volume):
        self.media_player.audio_set_volume(int(volume))


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
        if self.media_player.is_playing():
            self.window.after(500, self.update_progress_bar)  # Update every second


    # Playlist Methods
    def add_to_playlist(self):
        file_paths = filedialog.askopenfilenames(defaultextension=".*", filetypes=[("All Files", "*.*")])

        if not file_paths:
            folder_path = filedialog.askdirectory()
            if folder_path:
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        if file.endswith((".mp3", ".wav", ".mp4", ".avi", ".mkv", ".flac", ".mov", ".wmv", ".ogg", ".m4a", ".m4v")):
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
        playlist = self.playlist.get(0, tk.END)
        with open("last_playlist.json", 'w') as f:
            json.dump(playlist, f)
        self.window.destroy()

    # Settings Methods
    def toggle_always_on_top(self):
        self.window.attributes('-topmost', self.always_on_top.get())

    def toggle_theme(self):
        self.style = ttk.Style()
        #self.style.theme_use('clam')  # Ensure the theme supports custom styling for buttons
        if self.dark_mode.get():
            self.window.configure(bg='#2E2E2E')  # Dark grey background for the root window
            self.style.configure('TLabel', background='#2E2E2E', foreground='white')
            self.style.configure('TCheckbutton', background='#2E2E2E', foreground='white')
            self.playlist.configure(bg='#4D4D4D', fg='white', selectbackground='#6E6E6E', selectforeground='white')
        else:
            self.window.configure(bg='#f7f7f7')  # Light background for the root window
            self.style.configure('TLabel', background='white', foreground='black')
            self.style.configure('TCheckbutton', background='white', foreground='black')
            self.playlist.configure(bg='white', fg='black', selectbackground='#D3D3D3', selectforeground='black')



if __name__ == "__main__":
    window = tk.Tk()
    player = MediaPlayer(window)
    window.mainloop()