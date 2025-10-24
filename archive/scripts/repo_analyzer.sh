#!/usr/bin/env bash

# Analisador de Repositório - Versão Bash
# Compatível com: Linux, macOS, BSD, WSL, Git Bash
# Uso: ./repo_analyzer.sh [diretório]

set -euo pipefail

# Configurações
readonly SCRIPT_VERSION="1.0.0"
readonly DEFAULT_PATH="."
readonly DEFAULT_TOP_FILES=20

# Diretórios para ignorar
readonly IGNORE_DIRS=(
    ".git" ".svn" ".hg" ".bzr"
    "node_modules" "venv" "env" ".env"
    "__pycache__" ".pytest_cache" ".tox"
    "dist" "build" ".idea" ".vscode"
    "vendor" "target" ".next" ".nuxt"
)

# Extensões binárias para ignorar
readonly BINARY_EXTS=(
    "png" "jpg" "jpeg" "gif" "bmp" "ico" "svg"
    "pdf" "doc" "docx" "xls" "xlsx"
    "zip" "tar" "gz" "rar" "7z"
    "exe" "dll" "so" "dylib"
    "pyc" "pyo" "class" "jar"
    "mp3" "mp4" "avi" "mov"
    "ttf" "otf" "woff" "woff2"
)

# Variáveis globais
REPO_PATH="${1:-$DEFAULT_PATH}"
INCLUDE_BINARY=false
EXPORT_JSON=""
TOP_N=$DEFAULT_TOP_FILES
USE_PARALLEL=true
VERBOSE=false

# Arrays para armazenar dados
declare -a FILE_PATHS=()
declare -a FILE_LINES=()
declare -a FILE_SIZES=()
declare -A EXT_STATS=()

# Cores (detecta se o terminal suporta)
if [[ -t 1 ]] && command -v tput &>/dev/null && tput colors &>/dev/null; then
    readonly RED=$(tput setaf 1)
    readonly GREEN=$(tput setaf 2)
    readonly YELLOW=$(tput setaf 3)
    readonly BLUE=$(tput setaf 4)
    readonly BOLD=$(tput bold)
    readonly RESET=$(tput sgr0)
else
    readonly RED=""
    readonly GREEN=""
    readonly YELLOW=""
    readonly BLUE=""
    readonly BOLD=""
    readonly RESET=""
fi

# Funções auxiliares
print_error() {
    echo "${RED}Erro: $1${RESET}" >&2
}

print_success() {
    echo "${GREEN}$1${RESET}"
}

print_info() {
    echo "${BLUE}$1${RESET}"
}

print_header() {
    echo
    echo "${BOLD}$1${RESET}"
    echo "$(printf '=%.0s' {1..80})"
}

# Verifica se deve ignorar o diretório
should_ignore_dir() {
    local dir_name="$1"
    for ignore in "${IGNORE_DIRS[@]}"; do
        [[ "$dir_name" == "$ignore" ]] && return 0
    done
    return 1
}

# Verifica se é arquivo binário pela extensão
is_binary_file() {
    local file="$1"
    local ext="${file##*.}"
    
    [[ "$INCLUDE_BINARY" == true ]] && return 1
    
    for binary_ext in "${BINARY_EXTS[@]}"; do
        [[ "${ext,,}" == "$binary_ext" ]] && return 0
    done
    return 1
}

# Conta linhas de um arquivo de forma eficiente
count_lines() {
    local file="$1"
    local lines=0
    
    # Verifica se o arquivo existe e é legível
    [[ ! -r "$file" ]] && echo "-1" && return
    
    # Tenta diferentes métodos baseado no que está disponível
    if command -v wc &>/dev/null; then
        # Método mais rápido: wc
        lines=$(wc -l < "$file" 2>/dev/null || echo "-1")
    elif command -v awk &>/dev/null; then
        # Alternativa: awk
        lines=$(awk 'END {print NR}' "$file" 2>/dev/null || echo "-1")
    else
        # Fallback: bash puro (mais lento)
        while IFS= read -r _; do
            ((lines++))
        done < "$file" 2>/dev/null || echo "-1"
    fi
    
    echo "$lines"
}

# Formata tamanho de arquivo
format_size() {
    local size=$1
    local units=("B" "KB" "MB" "GB" "TB")
    local unit_index=0
    local size_float=$size
    
    while (( $(echo "$size_float >= 1024" | bc -l 2>/dev/null || echo 0) )) && (( unit_index < 4 )); do
        size_float=$(echo "scale=1; $size_float / 1024" | bc -l 2>/dev/null || echo "$size_float")
        ((unit_index++))
    done
    
    printf "%.1f %s" "$size_float" "${units[$unit_index]}"
}

# Processa um arquivo
process_file() {
    local file="$1"
    local rel_path="${file#$REPO_PATH/}"
    
    # Ignora arquivos ocultos
    [[ "$(basename "$file")" == .* ]] && return
    
    # Ignora binários
    is_binary_file "$file" && return
    
    # Conta linhas
    local lines=$(count_lines "$file")
    [[ $lines -eq -1 ]] && return
    
    # Obtém tamanho
    local size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
    
    # Armazena dados
    FILE_PATHS+=("$rel_path")
    FILE_LINES+=("$lines")
    FILE_SIZES+=("$size")
    
    # Atualiza estatísticas por extensão
    local ext="${file##*.}"
    [[ "$ext" == "$file" ]] && ext="no_extension"
    
    if [[ -z "${EXT_STATS[$ext]:-}" ]]; then
        EXT_STATS[$ext]="1:$lines:$size"
    else
        IFS=':' read -r count total_lines total_size <<< "${EXT_STATS[$ext]}"
        EXT_STATS[$ext]="$((count + 1)):$((total_lines + lines)):$((total_size + size))"
    fi
}

# Processa diretório recursivamente
process_directory() {
    local dir="${1:-$REPO_PATH}"
    local file_count=0
    
    # Usa find para eficiência
    while IFS= read -r -d '' file; do
        process_file "$file"
        ((file_count++))
        
        # Mostra progresso a cada 100 arquivos
        if (( file_count % 100 == 0 )); then
            echo -ne "\r  Processando... $file_count arquivos analisados"
        fi
    done < <(find "$dir" -type f \
        $(printf "! -path '*/%s/*' " "${IGNORE_DIRS[@]}") \
        -print0 2>/dev/null)
    
    echo -ne "\r  Processados $file_count arquivos totais                    \n"
}

# Processa com GNU parallel se disponível
process_parallel() {
    if command -v parallel &>/dev/null && [[ "$USE_PARALLEL" == true ]]; then
        print_info "Usando GNU Parallel para processamento acelerado..."
        
        export -f count_lines is_binary_file should_ignore_dir
        export INCLUDE_BINARY
        export -a BINARY_EXTS IGNORE_DIRS
        
        find "$REPO_PATH" -type f \
            $(printf "! -path '*/%s/*' " "${IGNORE_DIRS[@]}") \
            2>/dev/null | \
        parallel --will-cite -j+0 --progress "
            file={}
            [[ \$(basename \"\$file\") == .* ]] && exit
            ext=\${file##*.}
            for binary_ext in ${BINARY_EXTS[*]}; do
                [[ \"\${ext,,}\" == \"\$binary_ext\" ]] && exit
            done
            lines=\$(wc -l < \"\$file\" 2>/dev/null || echo -1)
            [[ \$lines -eq -1 ]] && exit
            size=\$(stat -c%s \"\$file\" 2>/dev/null || echo 0)
            rel_path=\${file#$REPO_PATH/}
            echo \"\$rel_path:\$lines:\$size\"
        " | while IFS=':' read -r path lines size; do
            FILE_PATHS+=("$path")
            FILE_LINES+=("$lines")
            FILE_SIZES+=("$size")
        done
    else
        process_directory
    fi
}

# Exibe resultados
print_results() {
    local total_files=${#FILE_PATHS[@]}
    local total_lines=0
    local total_size=0
    
    # Calcula totais
    for i in "${!FILE_LINES[@]}"; do
        ((total_lines += FILE_LINES[i]))
        ((total_size += FILE_SIZES[i]))
    done
    
    # Header
    print_header "ANÁLISE DO REPOSITÓRIO: $(realpath "$REPO_PATH")"
    
    # Resumo geral
    echo
    echo "${BOLD}RESUMO GERAL:${RESET}"
    echo "  Total de arquivos: $(printf "%'d" $total_files)"
    echo "  Total de linhas: $(printf "%'d" $total_lines)"
    echo "  Total de tamanho: $(format_size $total_size)"
    if (( total_files > 0 )); then
        echo "  Média de linhas/arquivo: $((total_lines / total_files))"
    fi
    
    # Estatísticas por extensão
    echo
    echo "${BOLD}ESTATÍSTICAS POR TIPO DE ARQUIVO:${RESET}"
    printf "  %-15s %-10s %-12s %-10s\n" "Extensão" "Arquivos" "Linhas" "Tamanho"
    echo "  $(printf '=%.0s' {1..50})"
    
    # Ordena extensões por número de linhas
    for ext in $(for e in "${!EXT_STATS[@]}"; do
        IFS=':' read -r _ lines _ <<< "${EXT_STATS[$e]}"
        echo "$lines:$e"
    done | sort -rn | head -10 | cut -d: -f2); do
        IFS=':' read -r count lines size <<< "${EXT_STATS[$ext]}"
        printf "  %-15s %-10d %-12s %-10s\n" \
            ".$ext" "$count" "$(printf "%'d" $lines)" "$(format_size $size)"
    done
    
    # Top arquivos por linhas
    if (( total_files > 0 )); then
        echo
        echo "${BOLD}TOP $TOP_N ARQUIVOS POR LINHAS:${RESET}"
        printf "  %-10s %-10s %s\n" "Linhas" "Tamanho" "Arquivo"
        echo "  $(printf '=%.0s' {1..70})"
        
        # Cria array de índices ordenados
        local sorted_indices=($(
            for i in "${!FILE_LINES[@]}"; do
                echo "${FILE_LINES[i]}:$i"
            done | sort -rn | head -"$TOP_N" | cut -d: -f2
        ))
        
        for idx in "${sorted_indices[@]}"; do
            printf "  %-10d %-10s %s\n" \
                "${FILE_LINES[idx]}" \
                "$(format_size "${FILE_SIZES[idx]}")" \
                "${FILE_PATHS[idx]}"
        done
    fi
}

# Exporta para JSON
export_json() {
    local output_file="$1"
    local total_files=${#FILE_PATHS[@]}
    local total_lines=0
    local total_size=0
    
    for i in "${!FILE_LINES[@]}"; do
        ((total_lines += FILE_LINES[i]))
        ((total_size += FILE_SIZES[i]))
    done
    
    cat > "$output_file" <<EOF
{
  "repository": "$(realpath "$REPO_PATH")",
  "summary": {
    "total_files": $total_files,
    "total_lines": $total_lines,
    "total_size": $total_size,
    "average_lines_per_file": $((total_files > 0 ? total_lines / total_files : 0))
  },
  "files": [
EOF
    
    # Adiciona arquivos
    local first=true
    for i in "${!FILE_PATHS[@]}"; do
        [[ $first == false ]] && echo "," >> "$output_file"
        cat >> "$output_file" <<EOF
    {
      "path": "${FILE_PATHS[i]}",
      "lines": ${FILE_LINES[i]},
      "size": ${FILE_SIZES[i]}
    }
EOF
        first=false
    done
    
    echo -e "\n  ]\n}" >> "$output_file"
    print_success "Resultados exportados para: $output_file"
}

# Mostra ajuda
show_help() {
    cat <<EOF
${BOLD}Analisador de Repositório v$SCRIPT_VERSION${RESET}

${BOLD}USO:${RESET}
    $0 [opções] [diretório]

${BOLD}OPÇÕES:${RESET}
    -h, --help           Mostra esta ajuda
    -t, --top N          Mostra top N arquivos (padrão: $DEFAULT_TOP_FILES)
    -j, --json FILE      Exporta resultados para JSON
    -b, --binary         Inclui arquivos binários
    -s, --serial         Desativa processamento paralelo
    -v, --verbose        Modo verboso
    --version            Mostra versão

${BOLD}EXEMPLOS:${RESET}
    $0                   # Analisa diretório atual
    $0 /path/to/repo     # Analisa repositório específico
    $0 -t 50 -j out.json # Top 50 arquivos e exporta JSON

${BOLD}REQUISITOS:${RESET}
    - Bash 4+ (funciona com 3+ com limitações)
    - Comandos: find, wc (opcionais: parallel, bc)

${BOLD}PERFORMANCE:${RESET}
    - Repositório pequeno (<1000 arquivos): ~1s
    - Repositório médio (<10000 arquivos): ~5s  
    - Repositório grande (>50000 arquivos): ~20s com parallel

EOF
}

# Processa argumentos
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help
                exit 0
                ;;
            -t|--top)
                TOP_N="$2"
                shift 2
                ;;
            -j|--json)
                EXPORT_JSON="$2"
                shift 2
                ;;
            -b|--binary)
                INCLUDE_BINARY=true
                shift
                ;;
            -s|--serial)
                USE_PARALLEL=false
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            --version)
                echo "Analisador de Repositório v$SCRIPT_VERSION"
                exit 0
                ;;
            -*)
                print_error "Opção desconhecida: $1"
                show_help
                exit 1
                ;;
            *)
                REPO_PATH="$1"
                shift
                ;;
        esac
    done
}

# Função principal
main() {
    parse_args "$@"
    
    # Valida diretório
    if [[ ! -d "$REPO_PATH" ]]; then
        print_error "O caminho '$REPO_PATH' não existe ou não é um diretório!"
        exit 1
    fi
    
    print_info "Analisando repositório em: $(realpath "$REPO_PATH")"
    
    # Detecta recursos disponíveis
    if command -v parallel &>/dev/null && [[ "$USE_PARALLEL" == true ]]; then
        print_info "GNU Parallel detectado - processamento acelerado ativado"
    fi
    
    # Processa arquivos
    if [[ "$USE_PARALLEL" == true ]]; then
        process_parallel
    else
        process_directory
    fi
    
    # Verifica se encontrou arquivos
    if [[ ${#FILE_PATHS[@]} -eq 0 ]]; then
        print_error "Nenhum arquivo encontrado para análise!"
        exit 1
    fi
    
    # Exibe resultados
    print_results
    
    # Exporta JSON se solicitado
    if [[ -n "$EXPORT_JSON" ]]; then
        export_json "$EXPORT_JSON"
    fi
    
    print_success "Análise concluída!"
}

# Executa se não estiver sendo sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi