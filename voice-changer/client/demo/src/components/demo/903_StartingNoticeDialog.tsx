import React, { useMemo } from "react";
import { useGuiState } from "./001_GuiStateProvider";
import { isDesktopApp } from "../../const";
import { useAppRoot } from "../../001_provider/001_AppRootProvider";
import { useMessageBuilder } from "../../hooks/useMessageBuilder";

export const StartingNoticeDialog = () => {
    const guiState = useGuiState();
    const messageBuilderState = useMessageBuilder();
    
    useMemo(() => {
        messageBuilderState.setMessage(__filename, "click_to_start", { ja: "시작하려면 버튼을 클릭하세요.", en: "Click to start" });
        messageBuilderState.setMessage(__filename, "start", { ja: "시작", en: "start" });
    }, []);

    const dialog = useMemo(() => {
        const closeButtonRow = (
            <div className="body-row split-3-4-3 left-padding-1">
                <div className="body-item-text"></div>
                <div className="body-button-container body-button-container-space-around">
                    <div
                        className="body-button"
                        onClick={() => {
                            guiState.stateControls.showStartingNoticeCheckbox.updateState(false);
                        }}
                    >
                        {messageBuilderState.getMessage(__filename, "start")}
                    </div>
                </div>
                <div className="body-item-text"></div>
            </div>
        );

        const clickToStartMessage = (
            <div className="dialog-content-part">
                <div>{messageBuilderState.getMessage(__filename, "click_to_start")}</div>
            </div>
        );

        const content = (
            <div className="body-row">
                {clickToStartMessage}
            </div>
        );

        return (
            <div className="dialog-frame">
                <div className="dialog-title">AI-VTUBER</div>
                <div className="dialog-content">
                    {content}
                    {closeButtonRow}
                </div>
            </div>
        );
    }, []);

    return dialog;
};
