
# run_pipeline

from app.pipeline.video_pipeline import run_pipeline

if __name__ == "__main__":

    video_file = "storage/input/test-video2.mp4"
    translate_language = "hindi"  # Hindi language code
    run_pipeline(video_file, translate_language)