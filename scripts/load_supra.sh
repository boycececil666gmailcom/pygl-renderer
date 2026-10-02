#!/bin/bash

# Define ANSI colors
CYAN='\033[1;96m'
GREEN='\033[1;92m'
NC='\033[0m' # No Color

# Step 1/2: Activating Virtual Environment
echo -e "\n${CYAN}========================================================${NC}"
echo -e "${GREEN}>>> [1/2] [$(basename "$0")] Activating Virtual Environment${NC}"
echo -e "${CYAN}========================================================${NC}\n"

if [ -d "venv" ]; then
    source venv/Scripts/activate
else
    echo "Error: venv directory not found. Please make sure the virtual environment is set up."
    exit 1
fi

# Step 2/2: Launching Renderer with Toyota Supra glTF
echo -e "\n${CYAN}========================================================${NC}"
echo -e "${GREEN}>>> [2/2] [$(basename "$0")] Launching WebGPU Engine with Toyota Supra GLTF${NC}"
echo -e "${CYAN}========================================================${NC}\n"

./venv/Scripts/python main.py gltf/toyota_supra.gltf
