# Codex Quota Bar v1.10.2

## 简体中文

- 修正 `Alt + 滚轮`：无论鼠标当前位于哪里，都会左右移动额度标签本身，并保存新位置；不会向 MyDockFinder 发送滚轮事件。
- 增加单实例保护，避免重复启动造成多个透明标签和鼠标钩子叠加。
- MyDockFinder 短暂无法检测时，延长隐藏标签前的等待时间；记录界面回调错误，便于排查异常退出。
- 本工具面向 MyDockFinder 用户，使用透明标签叠加显示，不是 MyDockFinder 原生插件或独立悬浮组件。

## English

- Fixed `Alt + wheel`: from anywhere, it moves the quota label itself left or right and saves its position. It does not send wheel events to MyDockFinder.
- Added single-instance protection to prevent duplicate transparent labels and mouse hooks.
- The label now waits longer before hiding during brief MyDockFinder detection gaps. UI callback errors are logged for troubleshooting.
- Intended for MyDockFinder users. It displays a transparent overlay label, not a native MyDockFinder plugin or standalone floating widget.

## 日本語

- `Alt + ホイール`を修正しました。マウス位置を問わず使用量ラベル自体を左右に移動し、新しい位置を保存します。MyDockFinder へホイールイベントは送信しません。
- 複数の透明ラベルやマウスフックが重なるのを防ぐため、単一起動を追加しました。
- MyDockFinder の検出が一時的に途切れても、ラベルをすぐに非表示にしないよう待機時間を延長しました。UI コールバックのエラーも記録します。
- MyDockFinder ユーザー向けです。透明なラベルを重ねて表示するもので、ネイティブプラグインや独立したフローティングウィジェットではありません。

## 한국어

- `Alt + 휠` 동작을 수정했습니다. 마우스 위치와 관계없이 잔여량 라벨 자체를 좌우로 이동하고 위치를 저장합니다. MyDockFinder에 휠 이벤트를 보내지 않습니다.
- 여러 투명 라벨과 마우스 후크가 겹치지 않도록 단일 실행 보호를 추가했습니다.
- MyDockFinder 감지가 잠시 끊겨도 라벨을 바로 숨기지 않도록 대기 시간을 늘렸습니다. UI 콜백 오류도 기록합니다.
- MyDockFinder 사용자를 위한 도구입니다. 투명 라벨을 오버레이로 표시하며, 네이티브 플러그인이나 독립 플로팅 위젯이 아닙니다.
