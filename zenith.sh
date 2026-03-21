#!/bin/bash
# --- PROJECT ZENITH: SINGULARITY CODEX (ULTIMATE TRUTH EDITION) ---
# Version: 2026.09.99 | The Final Terminal Standard
# Author: The Pilot & Project Zenith
# Core Directives: Zero Latency, Total Automation, Unbroken State

set -e

# --- Metadata & System Paths ---
VERSION="2026.09.99"
REPO_URL="https://raw.githubusercontent.com/YOUR_USER/project-zenith/main/zenith.sh"
ZENITH_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

# --- Visual Branding ---
PURPLE='\033[1;35m'
CYAN='\033[1;36m'
GOLD='\033[1;33m'
GREEN='\033[1;32m'
RED='\033[1;31m'
NC='\033[0m'

Z_LOGO="
  ███████╗███████╗███╗   ██╗██╗████████╗██╗  ██╗
  ╚══███╔╝██╔════╝████╗  ██║██║╚══██╔══╝██║  ██║
    ███╔╝ █████╗  ██╔██╗ ██║██║   ██║   ███████║
   ███╔╝  ██╔══╝  ██║╚██╗██║██║   ██║   ██╔══██║
  ███████╗███████╗██║ ╚████║██║   ██║   ██║  ██║
  ╚══════╝╚══════╝╚═╝  ╚═══╝╚═╝   ╚═╝   ╚═╝  ╚═╝
             THE ULTIMATE TRUTH
"

log() { echo -e "${CYAN}[ZENITH]${NC} $1"; }
warn() { echo -e "${GOLD}[WARNING]${NC} $1"; }

# --- 1. Distro Detection ---
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
    else
        DISTRO="unknown"
    fi
}

# --- 2. Orbital Engine (Visual Physics) ---
apply_orbit() {
    local orbit=$1
    mkdir -p ~/.config/ghostty/shaders
    G_CONF="$HOME/.config/ghostty/config"
    S_PATH="$HOME/.config/ghostty/shaders/zenith.glsl"

    touch "$G_CONF"

    case $orbit in
        celestial)
            log "Orbit Shift: CELESTIAL (Bio-Reactive Nebula)"
            sed -i 's/theme = .*/theme = catppuccin-mocha/' "$G_CONF" 2>/dev/null || echo "theme = catppuccin-mocha" >> "$G_CONF"
            cat <<EOF > "$S_PATH"
void mainImage(out vec4 f, in vec2 c) {
    vec2 uv = c/iResolution.xy;
    float t = iTime * 0.08;
    float pulse = sin(iTime * 1.5) * 0.05 + 0.95;
    vec3 col = 0.5 + 0.5*cos(t+uv.xyx+vec3(0,2,4));
    f = vec4(col * 0.1 * pulse, 0.9) * smoothstep(1.2, 0.2, distance(uv, vec2(0.5)));
}
EOF
            ;;
        matrix)
            log "Orbit Shift: MATRIX (Digital Torrent)"
            sed -i 's/theme = .*/theme = Monokai Pro/' "$G_CONF" 2>/dev/null || echo "theme = Monokai Pro" >> "$G_CONF"
            cat <<EOF > "$S_PATH"
void mainImage(out vec4 f, in vec2 c) {
    vec2 uv = c/iResolution.xy;
    float r = fract(sin(dot(vec2(floor(uv.x*50.0), floor(uv.y*30.0+iTime*15.0)), vec2(12.9898,78.233)))*43758.5453);
    f = vec4(0.0, r > 0.92 ? r : 0.0, 1.0) * 0.25;
}
EOF
            ;;
        quantum)
            log "Orbit Shift: QUANTUM (Grid Topology)"
            sed -i 's/theme = .*/theme = tokyo-night/' "$G_CONF" 2>/dev/null || echo "theme = tokyo-night" >> "$G_CONF"
            cat <<EOF > "$S_PATH"
void mainImage(out vec4 f, in vec2 c) {
    vec2 p = (c.xy * 2.0 - iResolution.xy) / min(iResolution.x, iResolution.y);
    float t = iTime * 0.5;
    float grid = max(step(0.98, fract(p.x * 10.0 + t)), step(0.98, fract(p.y * 10.0 + t)));
    f = vec4(0.1, 0.3, 0.8, 1.0) * grid * 0.3 + vec4(0.02, 0.02, 0.05, 1.0);
}
EOF
            ;;
        void)
            log "Orbit Shift: VOID (Absolute Stealth)"
            sed -i 's/theme = .*/theme = blackmetal/' "$G_CONF" 2>/dev/null || echo "theme = blackmetal" >> "$G_CONF"
            echo "void mainImage(out vec4 f, in vec2 c){f=vec4(0.0,0.0,0.0,1.0);}" > "$S_PATH"
            ;;
    esac
}

# --- 2.5 Celestial Sync ---
celestial_sync() {
    HOUR=$(date +%H)
    if [ "$HOUR" -ge 6 ] && [ "$HOUR" -lt 16 ]; then 
        apply_orbit celestial
    elif [ "$HOUR" -ge 16 ] && [ "$HOUR" -lt 20 ]; then 
        apply_orbit quantum
    elif [ "$HOUR" -ge 20 ] && [ "$HOUR" -lt 23 ]; then 
        apply_orbit matrix
    else 
        apply_orbit void
    fi
}

# --- 3. Telemetry Check ---
zenith_check() {
    log "Initiating Global Diagnostics..."
    echo "--------------------------------------------------"
    if glxinfo | grep -q "renderer"; then 
        echo -e "${GREEN}✔ GPU Engine:${NC} Active ($(glxinfo | grep "renderer string" | cut -d: -f2 | xargs))"
    else 
        echo -e "${RED}✘ GPU Engine:${NC} Software Fallback"
    fi
    
    echo -ne "${CYAN}Testing Neural Synapses (Llama 3.2)...${NC} "
    if systemctl is-active --quiet ollama; then
        start=$(date +%s%N); ollama run llama3.2:3b "echo ok" > /dev/null 2>&1; end=$(date +%s%N)
        echo -e "${GREEN}$(( (end - start) / 1000000 ))ms latency${NC}"
    else
        echo -e "${RED}✘ Offline${NC}"
    fi
    echo "--------------------------------------------------"
}

# --- 4. Deployment Core (The Singularity Event) ---
deploy_zenith() {
    detect_distro
    log "Initiating Singularity Protocol for $DISTRO..."

    # 4.1 Install the Modern Toolchain (Replacing the legacy utilities)
    if [ "$DISTRO" == "fedora" ]; then
        sudo dnf copr enable -y alternateved/ghostty varlad/zellij varlad/yazi
        sudo dnf install -y ghostty zellij yazi btop starship fastfetch ollama jetbrains-mono-fonts-all mesa-utils zoxide eza fzf ripgrep bat
    elif [ "$DISTRO" == "arch" ] || [ "$DISTRO" == "archarm" ]; then
        sudo pacman -S --needed --noconfirm ghostty zellij yazi btop starship fastfetch ollama ttf-jetbrains-mono-nerd mesa-utils zoxide eza fzf ripgrep bat
    else
        warn "Unsupported distro. Install dependencies manually: ghostty zellij yazi btop starship fastfetch ollama zoxide eza fzf ripgrep bat"
    fi

    # 4.2 Start AI Engine
    log "Waking Local Intelligence..."
    sudo systemctl enable --now ollama || true
    if ! ollama list | grep -q "llama3.2:3b"; then
        log "Downloading Neural Weights (One-time process)..."
        ollama pull llama3.2:3b
    fi

    # 4.3 Configure Ghostty & Zellij
    mkdir -p ~/.config/ghostty/shaders ~/.config/zellij/layouts ~/.config/starship
    
    cat <<EOF > "$HOME/.config/ghostty/config"
font-family = "JetBrainsMono Nerd Font"
font-size = 13
window-background-opacity = 0.85
window-blur-radius = 45
window-decoration = false
custom-shader-animation = true
keybind = global:alt+space=toggle_quick_terminal
confirm-close-surface = false
EOF

    cat <<EOF > "$HOME/.config/zellij/layouts/zenith.kdl"
layout {
    pane split_direction="vertical" {
        pane size="65%"
        pane split_direction="horizontal" {
            pane command="btop" size="45%"
            pane command="yazi" size="55%"
        }
    }
    pane size=1 borderless=true { plugin location="zellij:compact-bar"; }
}
EOF

    # 4.4 Futuristic Starship Prompt
    cat <<EOF > "$HOME/.config/starship.toml"
format = """[╭─](bold purple)\$directory\$git_branch\$git_status\n[╰─](bold purple)[▲](bold cyan) """
[directory]
style = "bold cyan"
truncate_to_repo = false
[git_branch]
symbol = " "
style = "bold purple"
EOF

    # 4.5 Bash Injection (The Magic)
    if ! grep -q "PROJECT ZENITH" ~/.bashrc; then
        # Block 1: Setup variables and aliases (Evaluates $ZENITH_DIR dynamically)
        cat <<EOF >> ~/.bashrc

# --- PROJECT ZENITH ---
# The Ultimate Truth of Terminal Performance
eval "\$(starship init bash)"
eval "\$(zoxide init bash)"

# Core Aliases
alias zenith="$ZENITH_DIR/zenith.sh"
alias zen="$ZENITH_DIR/zenith.sh"
alias warp="$ZENITH_DIR/zenith.sh warp"
alias dash="zellij attach zenith-core || zellij --layout zenith -s zenith-core"

# Holographic File System (HFS) Overrides
alias ls="eza --icons --git --color=always --group-directories-first"
alias ll="eza -alF --icons --git --color=always --group-directories-first"
alias tree="eza --tree --icons"
alias cat="bat --style=plain --paging=never"
alias cd="z"
EOF

        # Block 2: AI Functions (Quoted heredoc so bash logic writes cleanly)
        cat << 'EOF' >> ~/.bashrc

# 1. Navigator: Translates English to Bash
nav() {
    echo -e "\033[1;35m🛰 [Navigator] Mapping request...\033[0m"
    local raw_cmd=$(ollama run llama3.2:3b "You are a Linux terminal expert. OS: Linux. PWD: $PWD. User intent: $*. Provide ONLY the exact bash command. No markdown formatting, no explanation, no quotes." 2>/dev/null)
    local cmd=$(echo "$raw_cmd" | sed -e 's/^```bash//g' -e 's/^```//g' -e 's/```$//g' | xargs)
    echo -e "\033[1;36mCommand:\033[0m $cmd"
    echo -n "Execute? (y/n) " && read -r c
    [[ "$c" == "y" ]] && eval "$cmd"
}

# 2. Auto-Medic: Fixes broken commands instantly
fix() {
    local last_cmd=$(history | tail -n2 | head -n1 | sed -e 's/^[ ]*[0-9]*[ ]*//')
    echo -e "\033[1;31m⚕️ Diagnosing failure in:\033[0m $last_cmd"
    local error_out=$(eval "$last_cmd" 2>&1 >/dev/null)
    echo -e "\033[1;90mError Log: $error_out\033[0m"
    echo -e "\033[1;35m🧬 Synthesizing remedy...\033[0m"
    
    local remedy=$(ollama run llama3.2:3b "The linux command '$last_cmd' failed with error: '$error_out'. Provide ONLY the exact bash command to fix this. No markdown, no explanation." 2>/dev/null)
    local clean_remedy=$(echo "$remedy" | sed -e 's/^```bash//g' -e 's/^```//g' -e 's/```$//g' | xargs)
    
    echo -e "\033[1;32mRemedy:\033[0m $clean_remedy"
    echo -n "Apply fix? (y/n) " && read -r c
    [[ "$c" == "y" ]] && eval "$clean_remedy"
}
# --- END PROJECT ZENITH ---
EOF
    fi

    celestial_sync
    echo -e "${PURPLE}$Z_LOGO${NC}"
    log "Deployment Successful. Restart your terminal to enter the Singularity."
}

# --- Router ---
case "$1" in
    sync)      celestial_sync ;;
    orbit)     apply_orbit "$2" ;;
    warp)      clear; echo -e "${PURPLE}Synchronizing Dimensions...${NC}"; fastfetch --logo-type small ;;
    check)     zenith_check ;;
    help|--help)
        echo -e "${GOLD}ZENITH CORE COMMANDS:${NC}"
        echo -e "  ${CYAN}zen orbit [celestial|matrix|quantum|void]${NC} : Hot-swap reality shaders"
        echo -e "  ${CYAN}dash${NC}                                    : Enter persistent quantum workspace"
        echo -e "  ${CYAN}nav \"your intent\"${NC}                       : AI generates terminal commands"
        echo -e "  ${CYAN}fix${NC}                                     : AI auto-diagnoses last failed command"
        ;;
    *) deploy_zenith ;;
esac