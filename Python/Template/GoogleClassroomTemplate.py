from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# スコープを変更した場合は、既存トークンを削除して再認証する
SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.rosters.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.students.readonly",
]


class GoogleClassroom:
    def __init__(self):
        # プロジェクトルートを基準に credential/token の保存先を統一する
        self.root_dir = Path(__file__).resolve().parents[2]
        self.credentials_path = self._resolve_credentials_path()
        self.token_path = self.root_dir / "tokens" / "classroom_token.json"
        self.creds = None
        self.service = None
        self.authenticate()

    def _resolve_credentials_path(self) -> Path:
        # よく使う配置場所を順に探索する
        candidates = [
            self.root_dir / "tokens" / "credentials.json",
            self.root_dir / "credentials.json",
            Path(__file__).resolve().parent / "credentials.json",
        ]
        for path in candidates:
            if path.exists():
                return path
        raise FileNotFoundError(
            "credentials.json was not found. Place it in tokens/credentials.json."
        )

    def authenticate(self):
        # 既存トークンがあれば読み込む
        if self.token_path.exists():
            self.creds = Credentials.from_authorized_user_file(
                str(self.token_path), SCOPES
            )

        # トークンが無効ならリフレッシュ or OAuth フローで再取得
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            # 取得したトークンを保存して次回以降の認証を省略
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            self.token_path.write_text(self.creds.to_json(), encoding="utf-8")

        # Classroom API クライアントを生成
        self.service = build("classroom", "v1", credentials=self.creds)
        print("[Info] Connected to Google Classroom API.")

    def list_courses(self, page_size: int = 10):
        # 参加中のコース一覧を取得する
        try:
            response = self.service.courses().list(pageSize=page_size).execute()
            courses = response.get("courses", [])
            if not courses:
                print("No courses found.")
                return []

            print("\nCourses:")
            for course in courses:
                print(f"- {course.get('name')} (id={course.get('id')})")
            return courses
        except HttpError as error:
            print(f"[Error] Failed to fetch courses: {error}")
            return []

    def list_course_work(self, course_id: str, page_size: int = 20):
        # 指定コースの課題（CourseWork）一覧を取得する
        try:
            response = (
                self.service.courses()
                .courseWork()
                .list(courseId=course_id, pageSize=page_size)
                .execute()
            )
            course_work_list = response.get("courseWork", [])
            if not course_work_list:
                print("No course work found.")
                return []

            print(f"\nCourse work in {course_id}:")
            for course_work in course_work_list:
                title = course_work.get("title", "(no title)")
                state = course_work.get("state", "UNKNOWN")
                print(f"- {title} [{state}]")
            return course_work_list
        except HttpError as error:
            print(f"[Error] Failed to fetch course work: {error}")
            return []

    def list_students(self, course_id: str, page_size: int = 50):
        # 指定コースの生徒一覧を取得する
        try:
            response = (
                self.service.courses()
                .students()
                .list(courseId=course_id, pageSize=page_size)
                .execute()
            )
            students = response.get("students", [])
            if not students:
                print("No students found.")
                return []

            print(f"\nStudents in {course_id}:")
            for student in students:
                profile = student.get("profile", {})
                name = profile.get("name", {}).get("fullName", "(no name)")
                user_id = profile.get("id", "(no id)")
                print(f"- {name} (userId={user_id})")
            return students
        except HttpError as error:
            print(f"[Error] Failed to fetch students: {error}")
            return []


def main():
    # 学習用デモ:
    # 1) コース一覧取得
    # 2) 先頭コースの課題一覧・生徒一覧取得
    classroom = GoogleClassroom()
    courses = classroom.list_courses()
    if not courses:
        return

    first_course_id = courses[0]["id"]
    print(f"\n[Info] Demo target course id: {first_course_id}")
    classroom.list_course_work(first_course_id)
    classroom.list_students(first_course_id)


if __name__ == "__main__":
    main()
