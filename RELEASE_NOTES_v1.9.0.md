# Codex Quota Bar v1.9.0

## 简体中文

- 缩短白字转黑字的响应：每 50 毫秒采样一次，使用当前亮度直接判断，不再等待亮度滤波累积。
- 白字转黑字渐变约 100 毫秒，并保留亮暗回差以减少闪烁。
- 保持透明背景、MyDockFinder 顶栏定位、拖动、右键菜单和每分钟额度刷新。
- 显示方式是透明置顶浮层，不是 MyDockFinder 原生插件。

## English

- Faster white-to-dark text response: sample every 50 ms and decide from the current reading instead of waiting for a filtered value to catch up.
- The white-to-dark fade takes about 100 ms. A luminance dead band helps prevent flicker.
- Keeps the transparent overlay, MyDockFinder bar positioning, drag support, right-click menu, and one-minute quota refresh.
- The display is a transparent topmost overlay, not a native MyDockFinder plugin.

## 日本語

- 白文字から黒文字への切り替えを高速化しました。50 ミリ秒ごとにサンプリングし、平滑化値を待たず現在の明るさで判定します。
- 白から黒へのフェードは約 100 ミリ秒です。明るさのデッドバンドでちらつきを抑えます。
- 透明オーバーレイ、MyDockFinder バーへの追従、ドラッグ、右クリックメニュー、1 分ごとの更新を維持します。
- 表示方式は透明な最前面オーバーレイであり、MyDockFinder のネイティブプラグインではありません。

## 한국어

- 흰색에서 검은색 글자로 전환되는 응답을 개선했습니다. 50ms마다 샘플링하고 필터 값이 따라오기를 기다리지 않고 현재 밝기로 판단합니다.
- 흰색에서 검은색으로의 페이드는 약 100ms이며, 밝기 데드밴드로 깜박임을 줄입니다.
- 투명 오버레이, MyDockFinder 바 위치 추적, 드래그, 마우스 오른쪽 버튼 메뉴, 1분 간격 새로고침을 유지합니다.
- 표시 방식은 투명한 항상 위 오버레이이며 MyDockFinder 네이티브 플러그인은 아닙니다.
