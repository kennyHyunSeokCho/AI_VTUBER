#!/bin/bash

# VTuber Controller 빌드 스크립트
# 사용법: ./build.sh [mac|win|linux|all]

set -e

echo "🎭 VTuber Controller 빌드 스크립트"
echo "=================================="
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# 플랫폼 선택
PLATFORM=${1:-mac}

echo -e "${MAGENTA}선택된 플랫폼: $PLATFORM${NC}"
echo ""

# Node.js 확인
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js가 설치되어 있지 않습니다!${NC}"
    echo "https://nodejs.org/ 에서 설치하세요."
    exit 1
fi

echo -e "${GREEN}✓ Node.js 버전: $(node -v)${NC}"

# npm 확인
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm이 설치되어 있지 않습니다!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ npm 버전: $(npm -v)${NC}"
echo ""

# 필수 파일 확인
echo -e "${YELLOW}📋 필수 파일 확인 중...${NC}"

if [ ! -f "package.json" ]; then
    echo -e "${RED}❌ package.json 파일이 없습니다!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ package.json${NC}"

if [ ! -f "main.js" ]; then
    echo -e "${RED}❌ main.js 파일이 없습니다!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ main.js${NC}"

if [ ! -f "index.html" ]; then
    echo -e "${RED}❌ index.html 파일이 없습니다!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ index.html${NC}"

if [ ! -f "absolute2.py" ]; then
    echo -e "${YELLOW}⚠️  absolute2.py 파일이 없습니다. Python 백엔드가 작동하지 않을 수 있습니다.${NC}"
else
    echo -e "${GREEN}✓ absolute2.py${NC}"
fi

if [ ! -d "data" ]; then
    echo -e "${YELLOW}⚠️  data 폴더가 없습니다. 아바타 이미지가 없을 수 있습니다.${NC}"
else
    echo -e "${GREEN}✓ data 폴더${NC}"
fi

echo ""

# node_modules 확인 및 설치
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 의존성 설치 중...${NC}"
    npm install
    echo -e "${GREEN}✓ 의존성 설치 완료${NC}"
    echo ""
else
    echo -e "${GREEN}✓ node_modules 존재${NC}"
    echo ""
fi

# 이전 빌드 정리
if [ -d "dist-app" ]; then
    echo -e "${YELLOW}🧹 이전 빌드 파일 정리 중...${NC}"
    rm -rf dist-app
    echo -e "${GREEN}✓ 정리 완료${NC}"
    echo ""
fi

# 빌드 시작
echo -e "${MAGENTA}🚀 빌드 시작...${NC}"
echo ""

# 음성 학습 웹(voice_train) 프로덕션 빌드
if [ -d "voice_train" ]; then
    echo -e "${YELLOW}📦 voice_train(웹) 빌드 중...${NC}"
    pushd voice_train >/dev/null
    if [ ! -d node_modules ]; then
        npm install
    fi
    npx vite build
    popd >/dev/null
    echo -e "${GREEN}✓ voice_train 빌드 완료${NC}"
    echo ""
fi

case $PLATFORM in
    mac|macos)
        echo -e "${MAGENTA}🍎 macOS 앱 빌드 중...${NC}"
        npm run build:mac
        ;;
    win|windows)
        echo -e "${MAGENTA}🪟 Windows 앱 빌드 중...${NC}"
        npm run build:win
        ;;
    linux)
        echo -e "${MAGENTA}🐧 Linux 앱 빌드 중...${NC}"
        npm run build:linux
        ;;
    all)
        echo -e "${MAGENTA}🌍 모든 플랫폼 빌드 중...${NC}"
        npm run build:all
        ;;
    *)
        echo -e "${RED}❌ 알 수 없는 플랫폼: $PLATFORM${NC}"
        echo "사용법: ./build.sh [mac|win|linux|all]"
        exit 1
        ;;
esac

# 빌드 결과 확인
echo ""
if [ -d "dist-app" ]; then
    echo -e "${GREEN}🎉 빌드 완료!${NC}"
    echo ""
    echo -e "${MAGENTA}📦 빌드된 파일:${NC}"
    ls -lh dist-app/ | grep -v '^d' | awk '{print "   " $9 " (" $5 ")"}'
    echo ""
    echo -e "${GREEN}✨ dist-app/ 폴더에서 빌드 결과를 확인하세요!${NC}"
    echo ""
    
    # 실행 방법 안내
    case $PLATFORM in
        mac|macos)
            echo -e "${YELLOW}💡 실행 방법:${NC}"
            echo "   1. dist-app/*.dmg 파일을 더블클릭"
            echo "   2. 앱을 Applications 폴더로 드래그"
            echo "   3. Applications에서 실행"
            ;;
        win|windows)
            echo -e "${YELLOW}💡 실행 방법:${NC}"
            echo "   1. dist-app/*Setup*.exe 실행하여 설치"
            echo "   또는"
            echo "   2. dist-app/*.exe (포터블) 직접 실행"
            ;;
        linux)
            echo -e "${YELLOW}💡 실행 방법:${NC}"
            echo "   1. chmod +x dist-app/*.AppImage"
            echo "   2. ./dist-app/*.AppImage"
            ;;
    esac
else
    echo -e "${RED}❌ 빌드 실패! dist-app 폴더가 생성되지 않았습니다.${NC}"
    exit 1
fi

echo ""
echo -e "${MAGENTA}=================================="
echo -e "빌드 완료! 🎭✨"
echo -e "==================================${NC}"