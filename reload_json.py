"""
Модуль для замены шаблона формата json rpc-2.0 на актуальный
Работает с ответами типа Record и Recordset
Пример использования:
            rewrite_template(response=response, template_path='asserts/ДокОтгрИсх.СписокХраним.json')

     response: ответ метода (Объект Response)
     template_path: путь до шаблона
"""
import json
import re
from importlib import import_module
from ..assert_that import sort_json_rpc
import difflib
from copy import deepcopy


class RewriteTmp:
    """Класс для автозамены шаблона json"""
    template = None  # Шаблон
    response = None  # Ответ
    tmp_path = None  # Путь до шаблона
    data = None  # Модуль data.py (Словарь переменных)
    str_data = None  # Прочитанный файл (Строка)
    data_path = None  #
    r_variable = '{}([_a-zA-Zа-яА-Я][_a-zA-Zа-яА-Я0-9]*)'  # регулярка для переменной без делиметра
    changed_data_values = {}  # Измененные значения в ключах data.py
    changed_values = {}  # Измененные значения в шаблоне
    deleted_keys = []  # Удалённые ключи
    changed_keys = {}

    def __init__(self, template, response, tmp_path, data_path, delimeter):
        self.template = deepcopy(template)
        self.response = deepcopy(response)
        self.tmp_path = tmp_path
        self.data_path = data_path
        self.data = import_module('data').Data.__get_var_from_data_py__()
        self.str_data = self.read_data()
        self.r_variable = re.compile(self.r_variable.format(re.escape(delimeter)))
        self.rewrite_template()

    def rewrite_template(self):
        """Запуск автозамены"""
        assert self.template.get('result') and self.response.get('result') and \
               self.is_json_rpc(self.template['result']) and self.is_json_rpc(self.response['result']), \
            'Ответ и шаблон должны быть стандарта json rpc 2.0 и типа record / recordset'
        try:
            template, response = sort_json_rpc(self.template['result']), sort_json_rpc(self.response['result'])
            self.base_reload(template, response)
        except KeyError as e:
            raise e # Если в data не оказалось ключа
        except Exception:
            raise Exception('Не смогли выполнить автозамену шаблона') from None
        self.write_result()
        if self.changed_data_values:
            self.write_data()
        self.print_report()

    def base_reload(self, template, response):
        """
        Основная бизнес-логика замены полей
        :param template: шаблон (json)
        :param response: ответ (json)
        """
        # Заменяем структуру на актуальную
        self.reload_structure(template, response)
        # Далее итерируемся по "d" для замены рекордов
        if self.values_exist(template) and self.is_record(template):
            self.reload_record(template, response)
        if self.values_exist(template) and self.is_recordset(template):
            self.reload_recordset(template, response)

    def reload_record(self, template, response):
        """Автозамена в значениях record"""
        for i, value in enumerate(template['d']):
            tmp_value = value
            resp_value = response['d'][i]
            if self.is_record(tmp_value) or self.is_recordset(tmp_value):
                self.base_reload(sort_json_rpc(tmp_value), sort_json_rpc(resp_value))

    def reload_recordset(self, template, response):
        """Автозамена в значениях recordset"""
        for j, value in enumerate(template['d']):
            for i, sub_value in enumerate(value):
                tmp_value = sub_value
                resp_value = response['d'][j][i]
                if self.is_record(tmp_value) or self.is_recordset(tmp_value):
                    self.base_reload(sort_json_rpc(tmp_value), sort_json_rpc(resp_value))

    def reload_structure(self, template, response):
        """
        Замена структуры на актуальную
        :param template: шаблон (json)
        :param response: ответ (json)
        """
        tmp_structure = template['s']
        resp_structure = response['s']
        resp_values = response['d']
        value = None
        resp_keys = [i['n'] for i in response['s']]
        # Сначала удаляем пропавшие поля
        for tmp_matcher in deepcopy(tmp_structure):
            if tmp_matcher['n'] not in resp_keys:
                self.delete_key(template, self.find_index(template, tmp_matcher['n']))

        for i, resp_matcher in enumerate(resp_structure):
            # Ключи используем для поиска, так как тип может поменяться
            tmp_matcher = tmp_structure[i] if i < len(tmp_structure) else None
            # Значение value нужно для вставки в шаблон
            if self.values_exist(response):
                # Если recordset то value == все значения из массивов d
                value = [j[i] for j in resp_values] if self.is_recordset(template) else resp_values[i]
            # Поменялся тип поля
            if tmp_matcher and resp_matcher['n'] == tmp_matcher['n'] and resp_matcher['t'] != tmp_matcher['t']:
                self.change_key(template, resp_matcher, value, i)
            # Поле добавилось
            if resp_matcher not in tmp_structure:
                self.add_key(template, resp_matcher, value, i)

            if self.values_exist(template):
                self.rewrite_value(template, response, i)

    def add_key(self, tmp, matcher_s, matcher_d, index):
        """
        Добавление нового ключа
        :param tmp: шаблон
        :param matcher_s: новый ключ из ответа
        :param matcher_d: новое значение из ответа
        :param index: индекс вставки
        """
        tmp['s'].insert(index, matcher_s)
        if self.values_exist(tmp):
            if self.is_recordset(tmp):
                [value.insert(index, matcher_d[i]) for i, value in enumerate(tmp['d'])]
            elif self.is_record(tmp):
                tmp['d'].insert(index, matcher_d)

    def delete_key(self, tmp, index):
        """
        Удаление ключа вместе со значением
        :param tmp: шаблон
        :param index: индекс удаления
        :param replace: True - метод используется при перемещении поля, False - для удаления
        :return: Удаленное значение для использования при перемещении поля
        """
        self.deleted_keys.append(tmp['s'].pop(index))
        if self.values_exist(tmp) and self.is_recordset(tmp):
            return [value.pop(index) for i, value in enumerate(tmp['d'])]
        elif self.values_exist(tmp) and self.is_record(tmp):
            return tmp['d'].pop(index)

    def change_key(self, tmp, matcher_s, matcher_d, index):
        """
        Перезапись ключа
        :param tmp: шаблон
        :param matcher_s: новый ключ из ответа
        :param matcher_d: новое значение из ответа
        :param index: индекс вставки
        """
        item1_copy = json.dumps(tmp['s'][index], indent=3, sort_keys=True, ensure_ascii=False)
        item2_copy = json.dumps(matcher_s, indent=3, sort_keys=True, ensure_ascii=False)
        tmp['s'][index] = matcher_s
        self.changed_keys[item1_copy] = item2_copy
        if self.values_exist(tmp) and self.is_recordset(tmp):
            for i, value in enumerate(tmp['d']):
                value[index] = matcher_d[i]
        elif self.values_exist(tmp) and self.is_record(tmp):
            tmp['d'][index] = matcher_d

    def rewrite_value(self, tmp, resp, index):
        """
        Определение, в каком типе меняем значение
        :param tmp: шаблон
        :param resp: ответ
        :param index: индекс заменяемого значения
        """
        key = resp['s'][index]['n']
        tmp_index = self.find_index(tmp, key)
        if self.is_recordset(tmp):
            for i, value in enumerate(tmp['d']):
                tmp_value = value[index]
                resp_value = resp['d'][i][tmp_index]
                # Ответ или шаблон для замены не должны быть формата json rpc 2.0
                if not self.is_json_rpc(tmp_value) or not self.is_json_rpc(resp_value):
                    value[tmp_index] = self.check_value(tmp_value, resp_value, key, i)
        else:
            tmp_value = tmp['d'][tmp_index]
            resp_value = resp['d'][index]
            # Ответ или шаблон для замены не должны быть формата json rpc 2.0
            if not self.is_json_rpc(tmp_value) or not self.is_json_rpc(resp_value):
                tmp['d'][tmp_index] = self.check_value(tmp_value, resp_value, key)

    def check_value(self, tmp_value, resp_value, key, index=None):
        """
        Проверка значения с data.py и добавление в списки измененных значений
        :param tmp_value: значение шаблона
        :param resp_value: значение ответа
        :param key: ключ, в котором меняем
        :param index: индекс рекорда для отчета (для понимания, где заменили значение)
        :return: новое значение / переменная / ignore
        """
        result = tmp_value
        tmp_key = self.r_variable.match(str(result))
        if tmp_key and self.data[tmp_key.groups()[0]] != 'ignore' and self.data[tmp_key.groups()[0]] != resp_value:
            # Оборачиваем в кавычки, если строка (для вывода)
            resp_value = '\'%s\'' % resp_value if isinstance(resp_value, str) else resp_value
            self.changed_data_values[tmp_key.groups()[0]] = resp_value
        elif not tmp_key and tmp_value != 'ignore' and tmp_value != resp_value:
            result = resp_value
            self.add_changed_values(tmp_value, resp_value, key, index)
        return result

    def add_changed_values(self, tmp_value, resp_value, key, index):
        """Добавление в словарь измененных значений с обработкой для вывода"""
        tmp = '\n\td[{0}]: \n\t\t- {1}\n\t\t+ {2}\n\t'
        if isinstance(index, int) and key in self.changed_values.keys():
            self.changed_values[key] += tmp.format(index, tmp_value, resp_value)
        elif isinstance(index, int) and key not in self.changed_values.keys():
            self.changed_values[key] = tmp.format(index, tmp_value, resp_value)
        else:
            self.changed_values[key] = '\n- {0}\n+ {1}'.format(tmp_value, resp_value)

    @staticmethod
    def find_index(input_dict, parameter_name):
        """Находим индекс параметра в словаре"""

        result = None
        for item in input_dict['s']:
            if parameter_name == item['n']:
                result = input_dict['s'].index(item)
        return result

    @staticmethod
    def is_record(value):
        """Проверка валидности record"""
        return isinstance(value, dict) and value.get('_type') == 'record' and value.get('s') and value.get(
            's') != 'ignore'

    @staticmethod
    def is_json_rpc(value):
        """Проверка на соответствие типу json rpc 2.0"""
        return isinstance(value, dict) and value.get('_type') in ['record', 'recordset']

    @staticmethod
    def is_recordset(value):
        """Проверка валидности recordset"""
        return isinstance(value, dict) and value.get('_type') == 'recordset' and value.get('s') and value.get(
            's') != 'ignore'

    @staticmethod
    def values_exist(tmp):
        """Проверка, что поле d валидно"""
        return tmp['d'] and tmp['d'] != 'ignore'

    @staticmethod
    def read_data():
        """Чтение data.py"""
        with open('data.py', 'r', encoding='utf-8') as f:
            return f.read()

    def print_report(self):
        """
        Выводим информацию об изменившихся значениях и удалённых полях
        """
        changed_values = ''
        deleted_keys = ''
        changed_keys = ''
        changed_data_values = ''
        if self.changed_values:
            changed_values = '\nИзменены значения в шаблоне:\n' + \
                             '' + '\n'.join([i[0] + i[1] for i in self.changed_values.items()]) + '\n'
        if self.deleted_keys:
            deleted_keys = 'Из шаблоны удалены поля:\n' + \
                           ''.join(json.dumps(self.deleted_keys, indent=3, ensure_ascii=False)) + '\n'
        if self.changed_keys:
            for k, v in self.changed_keys.items():
                diff_str = ''.join(difflib.ndiff(k.splitlines(1), v.splitlines(1)))
                changed_keys += diff_str
            changed_keys = 'В шаблоне заменили тип значения в ключах:\n' + changed_keys
        if self.changed_data_values:
            changed_data_values = 'Изменены переменные в ' + self.data_path + ':\n\t{}\n'.format(
                '\n\t'.join([str(k + ' = ' + str(v)) for k, v in self.changed_data_values.items()]))
        result = deleted_keys + changed_keys + changed_values + changed_data_values
        # Исключения используем, чтобы акцентировать внимание
        if result:
            raise AssertionError(result + '\nУбедитесь, что это не ошибка')

    def write_data(self):
        """Запись нового словаря в data.py"""
        for k, v in self.changed_data_values.items():
            previous = str(k + ' = ' + str(self.data[k]))
            new = str(k + ' = ' + str(v))
            self.str_data = self.str_data.replace(previous, new)
        with open(self.data_path, 'w', encoding='utf-8') as f:
            f.write(self.str_data)

    def write_result(self):
        """Запись готового шаблона в файл"""
        with open(self.tmp_path, 'w', encoding='UTF-8') as f:
            f.write(json.dumps(self.template, indent=3, ensure_ascii=False))
