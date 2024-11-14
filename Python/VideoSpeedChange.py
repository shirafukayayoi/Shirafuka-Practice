from moviepy.editor import VideoFileClip, vfx


def main():
    video_path = input("動画ファイルのパスを入力してください: ")
    video_speed = float(input("再生速度を入力してください: "))
    video = VideoSpeedChange(video_path, video_speed)
    video.change_video_speed()


class VideoSpeedChange:
    def __init__(self, video_path, video_speed):
        self.video_path = video_path
        self.video_speed = video_speed

    def change_video_speed(self):
        try:
            clip = VideoFileClip(self.video_path)
            new_clip = clip.fx(vfx.speedx, self.video_speed)
            new_clip.write_videofile("output.mp4", codec="libx264", audio_codec="aac")
            print("動画の再生速度を変更しました。")
        except Exception as e:
            print(f"エラーが発生しました: {e}")


if __name__ == "__main__":
    main()
