안녕하세요... (거의) 최종 ui예요. . .

다른 폴더는 필요없고 
assets폴더에 이미지들이랑 html만 사용햇어요
다른 건 무시해 주세요

일단 voice 페이지 부분에 네모 상자에 현석 님 거 고대로 얹을 거고
my 페이지에는... 뭘 넣으면 조을지 모르겟어서 일단 냅뒀는데 하루 안에 만들 수 잇어서
좋은 생각 잇으면 공유해 주심 감사드리겟읍니다

그거 말고도 추가하면 조을 것 같은 부분 잇음 같이 말씀해 주세요
*8avatar.html은 지웟어야 하는데 잘못 올라간 거라 그냥 개처무시해 주세요. . .

제가 노트북에서만 만들고 맥으론 아직 안 켜봐서 어떨지 모르겟어요 ㅠ
이것도 일단 집 가서 봐볼게요

















# minimal-repro

**Quickly create and share examples of Electron app behaviors or bugs.**

> [!NOTE]
> This repro was renamed from `electron-quick-start` to clarify its purpose as a repro template. If you're looking to boostrap a new Electron app, check out the [Electron Forge](https://www.electronforge.io/) docs instead to get started!

Creating a minimal reproduction (or "minimal repro") is essential when troubleshooting Electron apps. By stripping away everything except the code needed to demonstrate a specific behavior or bug, it becomes easier for others to understand, debug, and fix issues. This focused approach saves time and ensures that everyone involved is looking at exactly the same problem without distractions.

A basic Electron application contains:

- `package.json` - Points to the app's main file and lists its details and dependencies.
- `main.js` - Starts the app and creates a browser window to render HTML. This is the app's **main process**.
- `index.html` - A web page to render. This is the app's **renderer process**.
- `preload.js` - A content script that runs before the renderer process loads.

You can learn more about each of these components in depth within the [Tutorial](https://electronjs.org/docs/latest/tutorial/tutorial-prerequisites).

## To Use

To clone and run this repository you'll need [Git](https://git-scm.com) and [Node.js](https://nodejs.org/en/download/) (which comes with [npm](http://npmjs.com)) installed on your computer. From your command line:

```bash
# Clone this repository
git clone https://github.com/electron/minimal-repro
# Go into the repository
cd minimal-repro
# Install dependencies
npm install
# Run the app
npm start
```

Note: If you're using Linux Bash for Windows, [see this guide](https://www.howtogeek.com/261575/how-to-run-graphical-linux-desktop-applications-from-windows-10s-bash-shell/) or use `node` from the command prompt.

## Resources for Learning Electron

- [electronjs.org/docs](https://electronjs.org/docs) - all of Electron's documentation
- [Electron Fiddle](https://electronjs.org/fiddle) - Electron Fiddle, an app to test small Electron experiments
- [Electron Forge](https://www.electronforge.io/) - Looking to bootstrap a new Electron app? Check out the Electron Forge docs to get started

## License

[CC0 1.0 (Public Domain)](LICENSE.md)
