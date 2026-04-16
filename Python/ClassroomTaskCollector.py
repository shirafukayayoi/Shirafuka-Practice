import argparse
import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.rosters.readonly",
    # OAuth同意画面では student-submissions 系が返るため、こちらを要求する
    "https://www.googleapis.com/auth/classroom.student-submissions.me.readonly",
    "https://www.googleapis.com/auth/classroom.student-submissions.students.readonly",
]


class ClassroomTaskCollector:
    def __init__(self, credentials_file: str | None = None):
        # Python/ClassroomTaskCollector.py -> repo root は parents[1]
        self.root_dir = Path(__file__).resolve().parents[1]
        self.credentials_path = self._resolve_credentials_path(credentials_file)
        self.token_path = self._resolve_token_path(self.credentials_path)
        self.creds = None
        self.service = None
        self.authenticate()

    def _resolve_credentials_path(self, credentials_file: str | None) -> Path:
        if credentials_file:
            candidates = [
                self.root_dir / "tokens" / credentials_file,
                self.root_dir / credentials_file,
                Path(__file__).resolve().parent / credentials_file,
            ]
            for path in candidates:
                if path.exists():
                    return path
            raise FileNotFoundError(
                f"{credentials_file} was not found. Place it in tokens/ or project root."
            )

        # ファイル指定がない場合は credentials*.json を自動検出
        auto_candidates = sorted((self.root_dir / "tokens").glob("credentials*.json"))
        if not auto_candidates:
            auto_candidates = sorted(self.root_dir.glob("credentials*.json"))

        if not auto_candidates:
            raise FileNotFoundError(
                "credentials.json was not found. Place credentials*.json in tokens/."
            )
        if len(auto_candidates) == 1:
            return auto_candidates[0]

        print("複数の認証ファイルが見つかりました。使うものを選んでください:")
        for index, path in enumerate(auto_candidates, start=1):
            project_id = self._read_project_id(path)
            project_note = f" (project_id={project_id})" if project_id else ""
            print(f"{index}. {path.name}{project_note}")

        while True:
            selected = input(f"番号を入力してください [1-{len(auto_candidates)}]: ").strip()
            if selected.isdigit():
                value = int(selected)
                if 1 <= value <= len(auto_candidates):
                    return auto_candidates[value - 1]
            print("入力が不正です。もう一度入力してください。")

    def _read_project_id(self, credentials_path: Path) -> str:
        try:
            data = json.loads(credentials_path.read_text(encoding="utf-8"))
            installed = data.get("installed", {})
            return installed.get("project_id", "")
        except (OSError, json.JSONDecodeError):
            return ""

    def _resolve_token_path(self, credentials_path: Path) -> Path:
        # credentials_2.json -> classroom_token_2.json のように分けて保存する
        suffix = credentials_path.stem.removeprefix("credentials").strip("_")
        token_name = "classroom_token.json" if not suffix else f"classroom_token_{suffix}.json"
        return self.root_dir / "tokens" / token_name

    def authenticate(self):
        if self.token_path.exists():
            self.creds = Credentials.from_authorized_user_file(
                str(self.token_path), SCOPES
            )

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            self.token_path.write_text(self.creds.to_json(), encoding="utf-8")

        self.service = build("classroom", "v1", credentials=self.creds)

    def class_list(self):
        try:
            response = self.service.courses().list(pageSize=20).execute()
            courses = response.get("courses", [])
            if not courses:
                print("No courses found.")
                return

            print("Courses:")
            for course in courses:
                print(f"- {course.get('name')} (id={course.get('id')})")
            class_list = [(course.get("id"), course.get("name")) for course in courses]
            return class_list
        except HttpError as error:
            print(f"An error occurred: {error}")
    
    def get_assignment(self, class_list):
        for class_id, class_name in class_list:
            print(f"\n{class_name} (id={class_id}):")
            try:
                response = self.service.courses().courseWork().list(courseId=class_id).execute()
                course_work = response.get("courseWork", [])
                if not course_work:
                    print("  No assignments found.")
                    continue
                assignments_count = 0
                for work in course_work:
                    assignments_count += 1
                    title = work.get("title")
                    due_date = work.get("dueDate", {})
                    due_time = work.get("dueTime", {})
                    if due_date and due_time:
                        due_str = (
                            f"{due_date.get('year')}-{due_date.get('month')}-{due_date.get('day')} "
                            f"{due_time.get('hours')}:{due_time.get('minutes')}"
                        )
                        print(f"  - {title} (Due: {due_str})")
                    else:
                        print(f"  - {title}")
                print(f"  Total assignments: {assignments_count}")
            except HttpError as error:
                print(f"  An error occurred: {error}")
        

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--credentials",
        help="認証に使う credentials ファイル名 (例: credentials_2.json)",
    )
    args = parser.parse_args()

    collector = ClassroomTaskCollector(credentials_file=args.credentials)
    print("Authentication successful. You can now use the Google Classroom API.")
    class_list = collector.class_list()
    assignments = collector.get_assignment(class_list)


if __name__ == "__main__":
    main()
