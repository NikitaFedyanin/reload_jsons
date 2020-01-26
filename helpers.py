from string import Template
import json
import re
import difflib
from importlib import import_module
import os
from reload_json import ReloadJson


def read_file(file_path, strip=True):
    """
    Чтение строки из файла file_path с заменой переменных на их значения из data
    :param file_path: Путь до файла с шаблоном ответа
    :param data: Экземпляр класса Data со значениями переменных для подстановки в шаблон
    :param encoding: Кодировка
    :param delimiter: Разделитель, который ставится перед переменными объявленными в шаблоне ответа
    :param id_pattern: Регулярное выражение, по которому находится переменная после разделителя
    :param strip: Необходимо ли устранять символы в конце строк
    :return: Строка, в которой заменили переменные, на их значения из data
    """
    # Экранируем символы в делиметре для подстановки в регулярку
    idpattern = r'''
    "{delimeter}(?:
    (?P<escaped>None)|
    (?P<named>[_a-zA-Zа-яА-Я][_a-zA-Zа-яА-Я0-9]*)"|
    (?P<braced>[_a-zA-Zа-яА-Я][_a-zA-Zа-яА-Я0-9]*)"|
    (?P<invalid>)
    )
    '''.format(delimeter=re.escape('$_'))

    tmp_str = ''
    if os.path.isfile(file_path):
        file = open(file_path, encoding='UTF-8')
        for line in file:
            if not line:
                continue
            if strip:
                line = line.strip()
            tmp_str += line
        tmp = type("MyTemplate", (Template,), {"pattern": idpattern})(tmp_str)
        data = import_module('data').Data.__get_var_from_data_py__()
        for k, v in data.items():
            data[k] = json.dumps(v, ensure_ascii=False, default=lambda x: 'attribute %s not serializable' % k)
        return tmp.substitute(**data)
    else:
        raise Exception('Файл с шаблоном ответа не найден по адресу {}'.format(file_path))


class DataForCompare:
    """Класс от которого наследуемся при создании класса с переменными для каждого стенда в сборке"""

    @classmethod
    def __get_var_from_data_py__(cls):
        """Служебный метод для получения словаря с переменными"""

        data_dict = {}
        for key in cls.__dict__.keys():
            if not key.startswith('__'):
                data_dict[key] = cls.__dict__[key]
        return data_dict


class Client:
    json_body = read_file('asserts/response.json')

    def compare_jsons(self, template):
        tmp_str = read_file(template, strip=False)
        resp_str = read_file(template, strip=False)
        assert tmp_str == self.json_body, ''.join(
            difflib.Differ().compare(tmp_str.splitlines(keepends=True),
                                     resp_str.splitlines(keepends=True)))

    def reload_template(self, tmp_path):
        tmp_str = read_file(tmp_path)
        ReloadJson(tmp_str, self.json_body)
