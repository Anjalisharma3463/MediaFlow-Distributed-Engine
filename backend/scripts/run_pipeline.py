
# run_pipeline

from app.pipeline.video_pipeline import run_pipeline

if __name__ == "__main__":

    video_file = "storage/input/test-video2.mp4"
    translate_language = "hindi"  # Hindi language code
    use_background_music = True  # Set to False if you don't want background music
    run_pipeline(video_file, translate_language,use_background_music)