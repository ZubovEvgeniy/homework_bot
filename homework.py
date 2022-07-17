import logging
import os
import time
from http import HTTPStatus
import statuses
import telegram

import requests
from dotenv import load_dotenv

import exceptions

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler()
)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщений в диалог."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(f'Сообщение в чат {TELEGRAM_CHAT_ID}: {message}')
    except telegram.error.TelegramError as error:
        logger.error(f'Ошибка: {error}')


def get_api_answer(current_timestamp):
    """Возвращает ответ API приведенный в json."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if response.status_code == HTTPStatus.OK.value:
            logger.info(f'Получен ответ от API {response.json()}')
            return response.json()
        else:
            logger.error(f'Сбой при запросе к эндпоинту!'
                         f'Ошибка: {response.status_code, response.text}')
            raise exceptions.TakeAPIError('Сбой при запросе к API!')
    except Exception as error:
        logger.error(f'Сбой при запросе к эндпоинту!'
                     f'Ошибка: {response.status_code, response.text}')
        raise exceptions.TakeAPIError(f'Сбой при запросе к API! {error}')


def check_response(response):
    """Проверка ответа API на корректность."""
    if isinstance(response['homeworks'], list):
        logger.info('Формат ответа соответствует ожидаемому')
        return response['homeworks']
    logger.error('Формат ответа НЕ соответствует ожидаемому')
    raise exceptions.TrueAPIError


def parse_status(homework):
    """Получение статуса домашней работы."""
    homework_name = homework.get('homework_name')
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
        verdict = statuses.HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError as error:
        logger.error(f'Неожиданный статус работы! {error}')
        raise KeyError


def check_tokens():
    """Проверка токенов."""
    token_list = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(token_list)


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    errors = False
    while True:
        try:
            if check_tokens():
                get_result = get_api_answer(current_timestamp)
                check_result = check_response(get_result)
                if check_result:
                    message = parse_status(check_result)
                    send_message(bot, message)
            else:
                logger.critical('Отсутствуют переменные окружения')
                raise Exception('Отсутствуют переменные окружения')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if errors:
                errors = False
                send_message(bot, message)
            logger.critical(message)

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
