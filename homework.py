import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import app_logger
from exceptions import HomeworkKeyError, HomeworkStatusError, StatusCodeError

load_dotenv()

logger = app_logger.get_logger(__name__)

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
    logger.info('Начата отправка сообщения в Telegramm.')
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logger.info('Сообщение отправлено в Telegramm.')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпойнту API-сервиса.
    В случае успешного запроса возвращает ответ API, преобразованный
    к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    request_params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }
    logger.info(f'Отправляем запрос к API {request_params}')
    response = requests.get(**request_params)
    logger.info('Получен ответ от API')

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

    if 'homeworks' not in response:
        raise HomeworkKeyError('Ответ API не содержит ключа "homeworks".')

    if 'current_date' not in response:
        raise HomeworkKeyError('Ответ API не содержит ключа "current_date".')

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

    if homework_status not in HOMEWORK_STATUSES:
        raise HomeworkStatusError(
            f'Неизвестный статус домашней рабоыт {homework_status}'
        )
    verdict = HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if not all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        logger.critical('Отсутствует обязательная переменная окружения.')
        return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Критическая ошибка. Отсутствуют переменные окружения.')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - 25 * 24 * 60 * 60
    prev_report = {'name': '', 'output': ''}
    current_report = {'name': '', 'output': ''}
    
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)

            if homeworks:
                homework = homeworks[0]
                current_report = {
                    'name': homework.get('homework_name'),
                    'output': parse_status(homework)
                }
            else:
                logger.debug('Новые статусы отсутствуют.')

            current_timestamp = int(time.time()) - 25 * 24 * 60 * 60

        except telegram.error.TelegramError as error:
            logging.error(error)

        except Exception as error:
            logging.error(error)
            current_report = {
                'name': homework.get('homework_name'),
                'output': f'Сбой в работе программы: {error}.'
            }

        finally:
            if prev_report != current_report:
                send_message(bot, current_report['output'])
            prev_report = current_report.copy()

            time.sleep(RETRY_TIME)


if __name__ == '__main__':

    main()
