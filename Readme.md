# Hydra Media Player
====================

A versatile media player built with Python and VLC. Made primarily to facilitate saving progress in playlists while watching videos or listening to music. When closing the program, progress will be saved and loaded on next start, unlike normal VLC functionality. Also offers basic audio analysis tools.

Features
--------
- Play, pause, stop, skip forward/backward tracks.
- Volume control.
- Fullscreen mode.
- Subtitle support for video files.
- Keyboard shortcuts for easy navigation.
- Audio device selection.
- Display information about the currently playing media.
- Automatic saving and loading of progress on startup and exit
- Basic audio analysis tools

Planned features:
- Picture-In-Picture popout window
- Improve audio device selection and subtitle choosing
- Improve UI with images, auto hiding, floating controls
- Improve audio analysis tools to be more robust and accurate
- Add visualizer for audio and EQ/Compression tools

Installation
------------
1. Clone this repository to your local machine:
   ```sh
   git clone https://github.com/yourusername/hydra-media-player.git
   cd hydra-media-player
   ```
2. Install dependencies using pip:
   ```sh
   pip install -r requirements.txt
   ```
3. Run the application:
   ```sh
   python main.py
   ```

Usage
-----
1. Open the media player by running `python main.py`.
2. Use the following keyboard shortcuts to control playback:
    - Spacebar: Play/Pause
    - Left Arrow: Previous Track
    - Right Arrow: Next Track
    - Shift + Up Arrow: Volume Up
    - Shift + Down Arrow: Volume Down
    - Control + O: Add to Playlist
    - Delete: Remove From Playlist
    - Control + S: Save Playlist
    - Control + L: Open Playlist
    - F: Toggle Fullscreen
    - C: Toggle Subtitles
3. Use the menu to select audio devices and view information about currently playing media.
4. Navigate through your playlist using the buttons provided or by selecting tracks from the sidebar.

Contributing
------------
Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change. Please make sure to update tests as appropriate.

License
-------
[MIT](https://choosealicense.com/licenses/mit/)