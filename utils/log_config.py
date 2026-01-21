import logging
import sys
import os
from pathlib import Path
from colorlog import ColoredFormatter

def setup_logging(
    log_level: str | None = None,
    log_level_file: str | None = None, 
    log_dir: str | Path | None = None,
    log_file_name: str = "application.log"
) -> logging.Logger:
    """
    Configura as definições de log para a aplicação.
    
    Obtém os níveis de log das variáveis de ambiente LOG_LEVEL e LOG_LEVEL_FILE,
    configura formatação colorida para o terminal e arquivo de log com timestamp.
    
    Args:
        log_level (str, optional): Nível de log para terminal. Se None, usa variável de ambiente LOG_LEVEL (padrão: 'INFO')
        log_level_file (str, optional): Nível de log para arquivo. Se None, usa variável de ambiente LOG_LEVEL_FILE (padrão: 'DEBUG')
        log_dir (str | Path, optional): Diretório para salvar logs. Se None, usa variável de ambiente LOG_DIR (padrão: diretório atual)
        log_file_name (str, optional): Nome do arquivo de log. Se None, usa 'application.log'
    
    Variáveis de ambiente suportadas:
        - LOG_LEVEL: Nível de log para terminal (padrão: 'INFO')
        - LOG_LEVEL_FILE: Nível de log para arquivo (padrão: 'DEBUG')
        - LOG_DIR: Diretório para salvar logs (padrão: diretório atual)
    
    Raises:
        ValueError: Se os níveis de log fornecidos forem inválidos.
        OSError: Se não conseguir criar o diretório de logs.
    
    Returns:
        logging.Logger: Logger configurado para a aplicação.
    """
    
    # Configurações - prioriza parâmetros, depois variáveis de ambiente, depois valores padrão
    log_level = (log_level or os.environ.get('LOG_LEVEL', 'INFO')).upper()
    log_level_file = (log_level_file or os.environ.get('LOG_LEVEL_FILE', 'DEBUG')).upper()
    log_dir = Path(log_dir or os.environ.get('LOG_DIR', os.getcwd()))
    log_file_name = log_file_name
    log_file_path = log_dir / log_file_name
    
    # Validação dos níveis de log
    valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
    if log_level not in valid_levels:
        raise ValueError(f"LOG_LEVEL inválido: '{log_level}'. Valores válidos: {valid_levels}")
    if log_level_file not in valid_levels:
        raise ValueError(f"LOG_LEVEL_FILE inválido: '{log_level_file}'. Valores válidos: {valid_levels}")
    
    # Configuração do diretório de logs
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(f"Não foi possível criar o diretório de logs em '{log_dir}': {e}") from e
    
    # Configuração da codificação de saída
    sys.stdout.reconfigure(encoding='utf-8') # pyright: ignore[reportAttributeAccessIssue]
    
    # Formatter para o terminal (colorido, apenas mensagem)
    terminal_formatter = ColoredFormatter(
        '%(log_color)s%(message)s',
        datefmt=None,
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'white',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    # Formatter para o arquivo (com timestamp, nível e mensagem)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para o terminal
    terminal_handler = logging.StreamHandler()
    terminal_handler.setFormatter(terminal_formatter)
    terminal_handler.setLevel(getattr(logging, log_level))
    
    # Handler para o arquivo (sempre DEBUG para capturar tudo)
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(log_level_file)
    
    # Configuração básica do logging (sempre DEBUG para capturar tudo)
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[terminal_handler, file_handler]
    )
    
    # Log inicial para indicar onde o arquivo está sendo salvo
    logger = logging.getLogger(__name__)
    logger.info(f"Arquivo de log criado em: {log_file_path}")
    
    return logger


def get_logger(name=None):
    """
    Obtém um logger configurado para o módulo especificado.
    
    Garante que setup_logging() tenha sido chamado antes.
    
    Args:
        name (str, optional):   Nome do logger (geralmente __name__). 
                                Se None, retorna o logger raiz.
    
    Returns:
        logging.Logger: Logger configurado.
    """
    return logging.getLogger(name)