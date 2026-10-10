# Codex Quota Bar v1.10.4

## 简体中文

- 修复额度标签闪烁：不再每次检测顶栏时都重新置顶窗口。
- 点击 MyDockFinder 顶栏后，仅延迟恢复一次标签层级；不抢焦点、不改变位置，也不拦截点击。
- 保留任意位置 `Alt + 滚轮` 移动额度标签、记住位置、单实例保护和短暂检测中断时的延迟隐藏。
- 本工具面向 MyDockFinder 用户，使用透明标签叠加显示，不是 MyDockFinder 原生插件或独立悬浮组件。

## English

- Fixed label flicker by removing repeated topmost updates during bar detection.
- After a MyDockFinder bar click, the app restores the label's z-order once after a short delay. It does not take focus, move the label, or intercept the click.
- Keeps `Alt + wheel` repositioning from anywhere, saved position, single-instance protection, and delayed hiding during brief detection gaps.
- Intended for MyDockFinder users. It displays a transparent overlay label, not a native MyDockFinder plugin or standalone floating widget.

## 日本語

- バーの検出ごとにウィンドウを最前面へ戻す処理をやめ、ラベルのちらつきを修正しました。
- MyDockFinder のバーをクリックした後だけ、短い遅延を置いてラベルの重なり順を一度復元します。フォーカスや位置は変えず、クリックも横取りしません。
- 場所を問わない `Alt + ホイール` による移動、位置の保存、単一起動、一時的な検出中断時の非表示遅延を維持します。
- MyDockFinder ユーザー向けです。透明なラベルを重ねて表示するもので、ネイティブプラグインや独立したフローティングウィジェットではありません。

## 한국어

- 바를 확인할 때마다 창을 최상위로 올리던 동작을 제거해 라벨 깜박임을 수정했습니다.
- MyDockFinder 바를 클릭한 뒤에만 짧은 지연 후 라벨의 창 순서를 한 번 복원합니다. 포커스나 위치를 바꾸지 않으며 클릭을 가로채지 않습니다.
- 어디서나 가능한 `Alt + 휠` 이동, 위치 저장, 단일 실행 보호, 일시적인 감지 중단 시 숨김 지연을 유지합니다.
- MyDockFinder 사용자를 위한 도구입니다. 투명 라벨 오버레이이며, 네이티브 플러그인이나 독립 플로팅 위젯이 아닙니다.
