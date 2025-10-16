import React, { useMemo, useState } from "react";
import { useAppState } from "../../../001_provider/001_AppStateProvider";
import { useGuiState } from "../001_GuiStateProvider";
import { useMessageBuilder } from "../../../hooks/useMessageBuilder";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

export type ModelSlotAreaProps = {};

const SortTypes = {
    slot: "slot",
    name: "name",
} as const;
export type SortTypes = (typeof SortTypes)[keyof typeof SortTypes];

export const ModelSlotArea = (_props: ModelSlotAreaProps) => {
    const { serverSetting, getInfo, webEdition } = useAppState();
    const guiState = useGuiState();
    const messageBuilderState = useMessageBuilder();
    const [sortType, setSortType] = useState<SortTypes>("slot");

    useMemo(() => {
        messageBuilderState.setMessage(__filename, "edit", { ja: "編集", en: "edit" });
    }, []);

    const modelTiles = useMemo(() => {
        if (!serverSetting.serverSetting.modelSlots) {
            return [];
        }
        const modelSlots =
            sortType == "slot"
                ? serverSetting.serverSetting.modelSlots
                : serverSetting.serverSetting.modelSlots.slice().sort((a, b) => {
                      return a.name.localeCompare(b.name);
                  });
        // 텍스트 드롭다운용 옵션으로 변환
        return modelSlots
            .filter((x) => x.modelFile && x.modelFile.length > 0)
            .map((x) => ({ label: x.name, value: x.slotIndex }));
    }, [serverSetting.serverSetting.modelSlots, sortType]);

    const modelSlotArea = useMemo(() => {
        const onModelSlotEditClicked = () => {
            guiState.stateControls.showModelSlotManagerCheckbox.updateState(true);
        };
        const sortSlotByIdClass = sortType == "slot" ? "model-slot-sort-button-active" : "model-slot-sort-button";
        const sortSlotByNameClass = sortType == "name" ? "model-slot-sort-button-active" : "model-slot-sort-button";
        const onChangeSelect = async (e: React.ChangeEvent<HTMLSelectElement>) => {
            const slotIndex = Number(e.target.value);
            // @ts-ignore
            const dummyModelSlotIndex = Math.floor(Date.now() / 1000) * 1000 + slotIndex;
            await serverSetting.updateServerSettings({ ...serverSetting.serverSetting, modelSlotIndex: dummyModelSlotIndex });
            setTimeout(() => {
                getInfo();
            }, 1000 * 2);
        };

        return (
            <div className="model-slot-area">
                <div className="model-slot-panel">
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px", width: "100%" }}>
                        <select className="body-select" value={serverSetting.serverSetting.modelSlotIndex as any} onChange={onChangeSelect}>
                            {modelTiles.map((opt) => (
                                <option key={(opt as any).value} value={(opt as any).value}>
                                    {(opt as any).label}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div className="model-slot-buttons">
                        <div className="model-slot-sort-buttons">
                            <div
                                className={sortSlotByIdClass}
                                onClick={() => {
                                    setSortType("slot");
                                }}
                            >
                                <FontAwesomeIcon icon={["fas", "arrow-down-1-9"]} style={{ fontSize: "1rem" }} />
                            </div>
                            <div
                                className={sortSlotByNameClass}
                                onClick={() => {
                                    setSortType("name");
                                }}
                            >
                                <FontAwesomeIcon icon={["fas", "arrow-down-a-z"]} style={{ fontSize: "1rem" }} />
                            </div>
                        </div>
                        <div className="model-slot-button" onClick={onModelSlotEditClicked}>
                            {messageBuilderState.getMessage(__filename, "edit")}
                        </div>
                    </div>
                </div>
            </div>
        );
    }, [modelTiles, sortType]);

    if (webEdition) {
        return <></>;
    }

    return modelSlotArea;
};
