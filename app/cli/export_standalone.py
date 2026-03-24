"""
Standalone 배포용 데이터 내보내기 CLI.

TODO: MVP 이후 구현
- User, Role 내보내기
- Partner + Contact 내보내기
- Setting, TermConfig 내보내기
- 지정 Project + 하위 엔티티 내보내기
- JSON 포맷 출력

Usage:
    python -m app.cli.export_standalone --modules common,infra --project-id 42 --output data.json
"""


def main() -> None:
    raise NotImplementedError("Export CLI is planned for post-MVP")


if __name__ == "__main__":
    main()
