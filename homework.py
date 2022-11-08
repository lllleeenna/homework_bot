import logging
import os
import sys
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
import telegram
from dotenv import load_dotenv

from exceptions import HomeworkKeyError, StatusCodeError

load_dotenv()


logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


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
    """Отправляет сообщение в чат."""
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logger.info('Сообщение отправлено в Telegramm.')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпойнту API-сервиса.
    В случае успешного запроса возвращает ответ API, преобразованный
    к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)

    if response.status_code != HTTPStatus.OK:
        raise StatusCodeError(
            f'Статус ответа {ENDPOINT} не соответствует ожидаемому.'
            f' Код ответа API: {response.status_code}'
        )
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректностью.
    Если ответ API соответствуюет ожиданиям, то возвращает список
    домашних работ.
    """
    if not isinstance(response, dict):
        raise TypeError('Ответ API не соответствует ожидаемому.')

    if not response:
        raise ValueError('Словарь полученный от API пуст.')

    if 'homeworks' not in response.keys():
        raise HomeworkKeyError('Ответ API не содержит ключа "homeworks".')

    list_homeworks = response.get('homeworks')

    if not isinstance(list_homeworks, list):
        raise TypeError('Ответ API не соответствует ожидаемому.')

    return list_homeworks


def parse_status(homework):
    """Извлекает из информации о домашней работе статус.
    Возвращает подготовленную для отправки строку.
    """
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    verdict = HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    env_variables = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for i in range(len(env_variables)):
        if not env_variables[i]:
            logger.critical(
                f'Отсутствует обязательная переменная окружения:'
                f'{ env_variables[i]}'
            )
            return False
    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    tokens = check_tokens()
    old_message = ''
    while tokens:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)
                send_message(bot, message)
            else:
                logger.debug('Новые статусы отсутствуют.')

            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except telegram.error.TelegramError as error:
            logging.error(error)
            time.sleep(RETRY_TIME)

        except Exception as error:
            logging.error(error)
            message = f'Сбой в работе программы: {error}.'
            if old_message != message:
                send_message(bot, message)
            old_message = message

            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
