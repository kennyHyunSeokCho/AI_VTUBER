import React, { useMemo } from "react";
import { INDEXEDDB_KEY_AUDIO_OUTPUT, isDesktopApp } from "../../../const";
import { useAppRoot } from "../../../001_provider/001_AppRootProvider";
import { useAppState } from "../../../001_provider/001_AppStateProvider";
import { useIndexedDB } from "@dannadori/voice-changer-client-js";
import { useMessageBuilder } from "../../../hooks/useMessageBuilder";

export type HeaderAreaProps = {
    mainTitle: string;
    subTitle: string;
};

export const HeaderArea = (props: HeaderAreaProps) => {
    const { appGuiSettingState } = useAppRoot();
    const messageBuilderState = useMessageBuilder();
    const { clearSetting } = useAppState();

    const { removeItem, removeDB } = useIndexedDB({ clientType: null });

    useMemo(() => {
        messageBuilderState.setMessage(__filename, "github", { ja: "github", en: "github" });
        messageBuilderState.setMessage(__filename, "manual", { ja: "マニュアル", en: "manual" });
        messageBuilderState.setMessage(__filename, "screenCapture", { ja: "録画ツール", en: "Record Screen" });
        // 커피/후원 문구 제거
    }, []);

    const githubLink = useMemo(() => {
        return isDesktopApp() ? (
            <span
                className="link tooltip"
                onClick={() => {
                    // @ts-ignore
                    window.electronAPI.openBrowser("about:blank");
                }}
            >
                <img src="./assets/icons/github.svg" />
                <div className="tooltip-text">{messageBuilderState.getMessage(__filename, "github")}</div>
            </span>
        ) : (
            <a className="link tooltip" href="about:blank" target="_blank" rel="noopener noreferrer">
                <img src="./assets/icons/github.svg" />
                <div className="tooltip-text">{messageBuilderState.getMessage(__filename, "github")}</div>
            </a>
        );
    }, []);

    const manualLink = useMemo(() => {
        return isDesktopApp() ? (
            <span
                className="link tooltip"
                onClick={() => {
                    // @ts-ignore
                    window.electronAPI.openBrowser("about:blank");
                }}
            >
                <img src="./assets/icons/help-circle.svg" />
                <div className="tooltip-text tooltip-text-100px">{messageBuilderState.getMessage(__filename, "manual")}</div>
            </span>
        ) : (
            <a className="link tooltip" href="about:blank" target="_blank" rel="noopener noreferrer">
                <img src="./assets/icons/help-circle.svg" />
                <div className="tooltip-text tooltip-text-100px">{messageBuilderState.getMessage(__filename, "manual")}</div>
            </a>
        );
    }, []);

    const toolLink = useMemo(() => {
        return isDesktopApp() ? (
            <div className="link tooltip">
                <img src="./assets/icons/tool.svg" />
                <div className="tooltip-text tooltip-text-100px">
                    <p
                        onClick={() => {
                            // @ts-ignore
                            window.electronAPI.openBrowser("about:blank");
                        }}
                    >
                        {messageBuilderState.getMessage(__filename, "screenCapture")}
                    </p>
                </div>
            </div>
        ) : (
            <div className="link tooltip">
                <img src="./assets/icons/tool.svg" />
                <div className="tooltip-text tooltip-text-100px">
                    <p
                        onClick={() => {
                            window.open("about:blank", "_blank", "noreferrer");
                        }}
                    >
                        {messageBuilderState.getMessage(__filename, "screenCapture")}
                    </p>
                </div>
            </div>
        );
    }, []);

    // BuyMeACoffee 요소 제거

    const headerArea = useMemo(() => {
        const onClearSettingClicked = async () => {
            await clearSetting();
            await removeItem(INDEXEDDB_KEY_AUDIO_OUTPUT);
            await removeDB();
            location.reload();
        };

        return (
            <div className="headerArea">
                <div className="title1">
                    <span className="title">{props.mainTitle}</span>
                    <span className="title-version-number">{appGuiSettingState.version}</span>
                    <span className="title-version-number">{appGuiSettingState.edition}</span>
                </div>
                {/* 상단 아이콘 제거, 필요 버튼만 유지 */}
                <div className="icons">
                    <span className="belongings">
                        <div className="belongings-button" onClick={onClearSettingClicked}>
                            clear setting
                        </div>
                    </span>
                </div>
            </div>
        );
    }, [props.subTitle, props.mainTitle, appGuiSettingState.version, appGuiSettingState.edition]);

    return headerArea;
};
