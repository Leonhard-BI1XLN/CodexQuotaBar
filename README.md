# Codex Quota Bar

**Languages:** [简体中文](#简体中文) · [English](#english) · [日本語](#日本語) · [한국어](#한국어)

> **适用对象：MyDockFinder 用户。本工具在 MyDockFinder 顶栏显示额度，不是独立的桌面悬浮组件。**
>
> **For MyDockFinder users: this displays quota on the MyDockFinder bar; it is not a standalone desktop floating widget.**
>
> **MyDockFinder ユーザー向けです。MyDockFinder のバーに残量を表示し、単独で浮かぶデスクトップウィジェットではありません。**
>
> **MyDockFinder 사용자를 위한 도구입니다. MyDockFinder 바에 잔여량을 표시하며, 독립적으로 떠 있는 데스크톱 위젯이 아닙니다.**

A lightweight Windows companion utility for MyDockFinder users that displays your remaining Codex quota in two lines:

```text
5h:  xx%
Week: xx%
```

## 简体中文

专为 MyDockFinder 用户设计，在 MyDockFinder 顶栏显示 Codex 5 小时和每周额度；不是独立的桌面悬浮组件。文字会根据背景亮度切换颜色。

### 下载与使用

1. 从[最新 Release](https://github.com/Leonhard-BI1XLN/CodexQuotaBar/releases/latest) 下载 `CodexQuotaBar.exe`。
2. 双击运行。无需在本工具中再次登录。
3. 右键标签可刷新额度、打开 ChatGPT、锁定位置或退出；未锁定时可拖动标签调整位置。

### 要求与工作方式

- Windows 10/11、MyDockFinder，以及已登录的 Codex 桌面版或 Codex CLI。
- 本工具通过本机 Codex `app-server` 的 `account/rateLimits/read` 接口读取额度，使用 Codex 已有的登录状态，不在本工具的设置文件中保存登录令牌。
- 这是透明置顶浮层，会跟随 MyDockFinder 顶栏位置；它不是 MyDockFinder 原生插件。MyDockFinder 目前没有公开的任意动态文字栏目接口文档。
- 额度数据每分钟刷新；找不到相应额度窗口时显示 `N/A`。接口或 Codex 协议变化可能影响兼容性。

### 从源码构建

安装 Python 3.13 后，在 PowerShell 中运行：

```powershell
.\打包EXE.ps1
```

打包脚本会下载 PyInstaller 和 Pillow，并在项目目录生成单文件 `CodexQuotaBar.exe`。

## English

A small Windows companion utility for MyDockFinder users. It displays your remaining Codex 5-hour and weekly quota on the MyDockFinder bar; it is not a standalone desktop floating widget. The text adapts to the background.

### Download and use

1. Download `CodexQuotaBar.exe` from the [latest Release](https://github.com/Leonhard-BI1XLN/CodexQuotaBar/releases/latest).
2. Run it. No separate sign-in is required.
3. Right-click the label to refresh quota, open ChatGPT, lock its position, or exit. Drag the label while unlocked to reposition it.

### Requirements and behavior

- Windows 10/11, MyDockFinder, and the Codex desktop app or CLI signed in to your account.
- The app reads quota through the local Codex `app-server` method `account/rateLimits/read`, reusing Codex's existing sign-in. It does not store the login token in its settings file.
- The label is a transparent, always-on-top overlay anchored to the MyDockFinder bar. It is **not** a native MyDockFinder plugin; no public API for arbitrary dynamic text items was found.
- Quota refreshes once per minute. A missing quota window is shown as `N/A`. Changes to the experimental app-server protocol may affect compatibility.

### Build from source

Install Python 3.13, then run in PowerShell:

```powershell
.\打包EXE.ps1
```

The script downloads PyInstaller and Pillow and builds a single-file `CodexQuotaBar.exe` in the project folder.

## 日本語

MyDockFinder ユーザー向けの小さな Windows 用ツールです。MyDockFinder のバーに Codex の 5 時間および週間の残り使用量を表示します。単独で浮かぶデスクトップウィジェットではありません。文字色は背景に合わせて切り替わります。

### ダウンロードと使い方

1. [最新の Release](https://github.com/Leonhard-BI1XLN/CodexQuotaBar/releases/latest) から `CodexQuotaBar.exe` をダウンロードします。
2. 起動します。このツールで別途ログインする必要はありません。
3. ラベルを右クリックすると、使用量の更新、ChatGPT を開く、位置の固定、終了ができます。ロックを解除した状態でドラッグすると位置を変更できます。

### 必要環境と動作

- Windows 10/11、MyDockFinder、ログイン済みの Codex デスクトップアプリまたは CLI が必要です。
- ローカル Codex `app-server` の `account/rateLimits/read` を使い、Codex の既存ログイン状態から使用量を取得します。ログイントークンを本ツールの設定ファイルには保存しません。
- 表示部分は透明な最前面オーバーレイで、MyDockFinder のバーに追従します。**MyDockFinder のネイティブプラグインではありません。** 任意の動的テキストを追加する公開 API は確認できていません。
- 使用量は 1 分ごとに更新します。該当する使用量ウィンドウがない場合は `N/A` と表示します。実験的な app-server API の変更により互換性が変わる可能性があります。

### ソースからビルド

Python 3.13 をインストールし、PowerShell で次を実行してください。

```powershell
.\打包EXE.ps1
```

スクリプトが PyInstaller と Pillow をダウンロードし、プロジェクトフォルダーに単一ファイルの `CodexQuotaBar.exe` を生成します。

## 한국어

MyDockFinder 사용자를 위한 작은 Windows 도구입니다. MyDockFinder 바에 Codex의 5시간 및 주간 잔여 사용량을 표시하며, 독립 데스크톱 플로팅 위젯이 아닙니다. 글자 색은 배경에 맞춰 바뀝니다.

### 다운로드 및 사용

1. [최신 Release](https://github.com/Leonhard-BI1XLN/CodexQuotaBar/releases/latest)에서 `CodexQuotaBar.exe`를 다운로드합니다.
2. 실행합니다. 이 도구에서 별도로 로그인할 필요가 없습니다.
3. 라벨을 마우스 오른쪽 버튼으로 클릭하면 사용량 새로고침, ChatGPT 열기, 위치 잠금 또는 종료를 할 수 있습니다. 잠금 해제 상태에서 라벨을 드래그해 위치를 바꿀 수 있습니다.

### 요구 사항 및 동작 방식

- Windows 10/11, MyDockFinder, 로그인된 Codex 데스크톱 앱 또는 CLI가 필요합니다.
- 로컬 Codex `app-server`의 `account/rateLimits/read` 메서드로 사용량을 읽으며 기존 Codex 로그인 상태를 재사용합니다. 로그인 토큰을 이 도구의 설정 파일에 저장하지 않습니다.
- 표시는 MyDockFinder 바에 고정되는 투명한 항상 위 오버레이입니다. **MyDockFinder 네이티브 플러그인은 아닙니다.** 임의의 동적 텍스트 항목을 추가하는 공개 API 문서는 확인되지 않았습니다.
- 사용량은 1분마다 새로고침됩니다. 해당 사용량 창을 찾을 수 없으면 `N/A`로 표시합니다. 실험적 app-server API가 바뀌면 호환성에 영향을 줄 수 있습니다.

### 소스에서 빌드

Python 3.13을 설치한 뒤 PowerShell에서 실행합니다.

```powershell
.\打包EXE.ps1
```

스크립트가 PyInstaller와 Pillow를 내려받고 프로젝트 폴더에 단일 파일 `CodexQuotaBar.exe`를 만듭니다.
