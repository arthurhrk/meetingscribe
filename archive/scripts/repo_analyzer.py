#!/usr/bin/env python3
"""
Script otimizado para analisar repositório: lista arquivos e conta linhas
Uso: python repo_analyzer.py [caminho_do_repositorio]
"""

import os
import sys
import argparse
import json
import mmap
import fnmatch
from pathlib import Path
from typing import Dict, List, Tuple, Generator, Optional, Set
from dataclasses import dataclass, asdict
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from functools import lru_cache
import multiprocessing

# Diretórios comuns para ignorar
DEFAULT_IGNORE_DIRS = frozenset({
    '.git', '.svn', '.hg', '.bzr',
    'node_modules', 'venv', 'env', '.env',
    '__pycache__', '.pytest_cache', '.tox',
    'dist', 'build', '.idea', '.vscode',
    'vendor', 'target', '.next', '.nuxt'
})

# Extensões de arquivos binários para ignorar
BINARY_EXTENSIONS = frozenset({
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.zip', '.tar', '.gz', '.rar', '.7z',
    '.exe', '.dll', '.so', '.dylib',
    '.pyc', '.pyo', '.class', '.jar',
    '.mp3', '.mp4', '.avi', '.mov',
    '.ttf', '.otf', '.woff', '.woff2'
})

# Tamanho do chunk para leitura de arquivos grandes
CHUNK_SIZE = 1024 * 1024  # 1MB

@dataclass(frozen=True, slots=True)
class FileInfo:
    """Estrutura otimizada para informações de arquivo"""
    path: str
    lines: int
    size: int
    
    @property
    @lru_cache(maxsize=1)
    def extension(self) -> str:
        """Retorna extensão do arquivo (cached)"""
        return Path(self.path).suffix or 'no_extension'


class GitignoreParser:
    """Parser eficiente para .gitignore"""
    
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.patterns = self._load_gitignore_patterns()
    
    def _load_gitignore_patterns(self) -> List[str]:
        """Carrega padrões do .gitignore se existir"""
        gitignore_path = self.root_path / '.gitignore'
        if not gitignore_path.exists():
            return []
        
        patterns = []
        try:
            with open(gitignore_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line)
        except:
            pass
        
        return patterns
    
    @lru_cache(maxsize=1024)
    def should_ignore(self, path: Path) -> bool:
        """Verifica se o path deve ser ignorado baseado no .gitignore (cached)"""
        rel_path = str(path.relative_to(self.root_path))
        
        for pattern in self.patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
            if path.is_dir() and fnmatch.fnmatch(rel_path + '/', pattern):
                return True
        
        return False


class OptimizedRepositoryAnalyzer:
    def __init__(self, path: str, ignore_dirs: Set[str] = None, 
                 ignore_binary: bool = True, use_gitignore: bool = True,
                 max_workers: Optional[int] = None):
        """
        Inicializa o analisador otimizado
        
        Args:
            path: Caminho do repositório
            ignore_dirs: Conjunto de diretórios para ignorar
            ignore_binary: Se deve ignorar arquivos binários
            use_gitignore: Se deve usar .gitignore
            max_workers: Número máximo de workers (None = auto)
        """
        self.path = Path(path)
        self.ignore_dirs = frozenset(ignore_dirs or DEFAULT_IGNORE_DIRS)
        self.ignore_binary = ignore_binary
        self.use_gitignore = use_gitignore
        self.gitignore_parser = GitignoreParser(self.path) if use_gitignore else None
        
        # Determina número ótimo de workers
        self.max_workers = max_workers or min(32, (multiprocessing.cpu_count() or 1) * 2)
        
        # Usa estruturas otimizadas
        self.files_data: List[FileInfo] = []
        self._stats_cache = {}
    
    @lru_cache(maxsize=512)
    def should_ignore_file(self, file_path: Path) -> bool:
        """Verifica se o arquivo deve ser ignorado (cached)"""
        # Ignora arquivos ocultos
        if file_path.name.startswith('.'):
            return True
        
        # Ignora binários se configurado
        if self.ignore_binary and file_path.suffix.lower() in BINARY_EXTENSIONS:
            return True
        
        # Verifica .gitignore
        if self.gitignore_parser and self.gitignore_parser.should_ignore(file_path):
            return True
        
        return False
    
    @staticmethod
    def count_lines_fast(file_path: Path) -> int:
        """
        Conta linhas de forma otimizada usando mmap para arquivos grandes
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Número de linhas ou -1 se erro
        """
        try:
            # Para arquivos pequenos, usa método tradicional
            file_size = file_path.stat().st_size
            if file_size == 0:
                return 0
            
            if file_size < CHUNK_SIZE:
                with open(file_path, 'rb') as f:
                    return sum(1 for _ in f)
            
            # Para arquivos grandes, usa mmap
            with open(file_path, 'rb') as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                    lines = 0
                    while mmapped_file.read(CHUNK_SIZE):
                        lines += mmapped_file.read(CHUNK_SIZE).count(b'\n')
                    return lines + 1
                    
        except (UnicodeDecodeError, PermissionError, OSError):
            return -1
    
    def get_files_generator(self, directory: Path = None) -> Generator[Path, None, None]:
        """
        Generator eficiente para arquivos (evita carregar tudo na memória)
        
        Args:
            directory: Diretório para analisar
            
        Yields:
            Caminhos de arquivos válidos
        """
        if directory is None:
            directory = self.path
        
        # Usa os.walk que é mais eficiente que Path.iterdir recursivo
        for root, dirs, files in os.walk(directory):
            root_path = Path(root)
            
            # Remove diretórios ignorados in-place (modifica dirs)
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            
            # Processa arquivos
            for file in files:
                file_path = root_path / file
                
                if not self.should_ignore_file(file_path):
                    yield file_path
    
    def process_file(self, file_path: Path) -> Optional[FileInfo]:
        """
        Processa um único arquivo
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            FileInfo ou None se erro
        """
        try:
            line_count = self.count_lines_fast(file_path)
            
            if line_count >= 0:
                relative_path = file_path.relative_to(self.path)
                return FileInfo(
                    path=str(relative_path),
                    lines=line_count,
                    size=file_path.stat().st_size
                )
        except:
            pass
        
        return None
    
    def analyze_parallel(self) -> None:
        """Análise paralela otimizada do repositório"""
        print(f"Usando {self.max_workers} workers para análise paralela...")
        
        # Coleta arquivos usando generator
        file_paths = list(self.get_files_generator())
        total_files = len(file_paths)
        
        if total_files == 0:
            return
        
        processed = 0
        # Usa ThreadPoolExecutor para I/O bound tasks
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submete todos os arquivos
            future_to_file = {
                executor.submit(self.process_file, file_path): file_path 
                for file_path in file_paths
            }
            
            # Processa resultados conforme ficam prontos
            for future in as_completed(future_to_file):
                result = future.result()
                if result:
                    self.files_data.append(result)
                
                processed += 1
                if processed % 100 == 0:
                    progress = (processed / total_files) * 100
                    print(f"  Progresso: {progress:.1f}% ({processed}/{total_files})", end='\r')
        
        print(f"  Analisados {len(self.files_data)} arquivos válidos                    ")
    
    @lru_cache(maxsize=1)
    def get_statistics_by_extension(self) -> Dict[str, Dict]:
        """Agrupa estatísticas por extensão (cached)"""
        stats = defaultdict(lambda: {'files': 0, 'lines': 0, 'size': 0})
        
        for file_info in self.files_data:
            ext = file_info.extension
            stats[ext]['files'] += 1
            stats[ext]['lines'] += file_info.lines
            stats[ext]['size'] += file_info.size
        
        return dict(stats)
    
    @staticmethod
    def format_size(size: int) -> str:
        """Formata tamanho em bytes (otimizado)"""
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_idx = 0
        size_float = float(size)
        
        while size_float >= 1024.0 and unit_idx < len(units) - 1:
            size_float /= 1024.0
            unit_idx += 1
        
        return f"{size_float:.1f} {units[unit_idx]}"
    
    def get_summary_stats(self) -> Dict:
        """Retorna estatísticas resumidas (cached)"""
        if not self._stats_cache:
            total_lines = sum(f.lines for f in self.files_data)
            total_files = len(self.files_data)
            total_size = sum(f.size for f in self.files_data)
            
            self._stats_cache = {
                'total_files': total_files,
                'total_lines': total_lines,
                'total_size': total_size,
                'avg_lines': total_lines / max(total_files, 1)
            }
        
        return self._stats_cache
    
    def print_results(self, show_files: bool = True, top_n: int = 20) -> None:
        """Imprime resultados de forma otimizada"""
        stats = self.get_summary_stats()
        
        print("=" * 80)
        print(f"ANÁLISE DO REPOSITÓRIO: {self.path}")
        print("=" * 80)
        
        # Resumo geral
        print(f"\nRESUMO GERAL:")
        print(f"  Total de arquivos: {stats['total_files']:,}")
        print(f"  Total de linhas: {stats['total_lines']:,}")
        print(f"  Total de tamanho: {self.format_size(stats['total_size'])}")
        print(f"  Média de linhas/arquivo: {stats['avg_lines']:.1f}")
        
        # Estatísticas por extensão
        print(f"\nESTATÍSTICAS POR TIPO DE ARQUIVO:")
        ext_stats = self.get_statistics_by_extension()
        
        # Ordena uma vez
        sorted_stats = sorted(ext_stats.items(), 
                            key=lambda x: x[1]['lines'], 
                            reverse=True)[:10]
        
        print(f"  {'Extensão':<15} {'Arquivos':<10} {'Linhas':<12} {'Tamanho':<10}")
        print("  " + "-" * 50)
        
        for ext, data in sorted_stats:
            print(f"  {ext:<15} {data['files']:<10} {data['lines']:<12,} "
                  f"{self.format_size(data['size']):<10}")
        
        # Lista top arquivos
        if show_files and self.files_data:
            print(f"\nTOP {min(top_n, len(self.files_data))} ARQUIVOS POR LINHAS:")
            
            # Usa heapq para top N eficiente em grandes listas
            import heapq
            top_files = heapq.nlargest(top_n, self.files_data, key=lambda x: x.lines)
            
            print(f"  {'Linhas':<10} {'Tamanho':<10} {'Arquivo'}")
            print("  " + "-" * 70)
            
            for file_info in top_files:
                print(f"  {file_info.lines:<10} "
                      f"{self.format_size(file_info.size):<10} "
                      f"{file_info.path}")
    
    def export_to_json(self, output_file: str) -> None:
        """Exporta para JSON de forma eficiente"""
        stats = self.get_summary_stats()
        
        data = {
            'repository': str(self.path),
            'summary': {
                'total_files': stats['total_files'],
                'total_lines': stats['total_lines'],
                'total_size': stats['total_size'],
                'average_lines_per_file': stats['avg_lines']
            },
            'statistics_by_extension': self.get_statistics_by_extension(),
            'files': [asdict(f) for f in sorted(self.files_data, 
                                               key=lambda x: x.lines, 
                                               reverse=True)[:100]]  # Limita para não criar JSONs gigantes
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\nResultados exportados para: {output_file}")
    
    def run(self) -> None:
        """Executa análise otimizada"""
        if not self.path.exists():
            print(f"Erro: O caminho '{self.path}' não existe!")
            return
        
        if not self.path.is_dir():
            print(f"Erro: '{self.path}' não é um diretório!")
            return
        
        print(f"Analisando repositório em: {self.path}")
        
        # Análise paralela
        self.analyze_parallel()
        
        if not self.files_data:
            print("Nenhum arquivo encontrado para análise!")
            return
        
        self.print_results()


def main():
    """Função principal otimizada"""
    parser = argparse.ArgumentParser(
        description='Analisador otimizado de repositório'
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Caminho do repositório (padrão: diretório atual)'
    )
    parser.add_argument(
        '--top',
        type=int,
        default=20,
        metavar='N',
        help='Mostra top N arquivos (padrão: 20)'
    )
    parser.add_argument(
        '--export-json',
        metavar='FILE',
        help='Exporta resultados para JSON'
    )
    parser.add_argument(
        '--include-binary',
        action='store_true',
        help='Inclui arquivos binários'
    )
    parser.add_argument(
        '--no-gitignore',
        action='store_true',
        help='Ignora arquivo .gitignore'
    )
    parser.add_argument(
        '--workers',
        type=int,
        metavar='N',
        help='Número de workers paralelos (padrão: auto)'
    )
    parser.add_argument(
        '--ignore-dirs',
        nargs='+',
        help='Diretórios adicionais para ignorar'
    )
    
    args = parser.parse_args()
    
    # Configura diretórios
    ignore_dirs = set(DEFAULT_IGNORE_DIRS)
    if args.ignore_dirs:
        ignore_dirs.update(args.ignore_dirs)
    
    # Cria analisador otimizado
    analyzer = OptimizedRepositoryAnalyzer(
        path=args.path,
        ignore_dirs=ignore_dirs,
        ignore_binary=not args.include_binary,
        use_gitignore=not args.no_gitignore,
        max_workers=args.workers
    )
    
    # Executa análise
    try:
        analyzer.run()
        
        if args.export_json:
            analyzer.export_to_json(args.export_json)
            
    except KeyboardInterrupt:
        print("\n\nAnálise interrompida pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\nErro: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()