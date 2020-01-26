import json


class ReloadJson:
    template = None
    response = None
    tmp_path = None

    def __init__(self, template, response, tmp_path):
        self.template = template
        self.response = response
        self.tmp_path = tmp_path
        self.base_reload(self.template['result'], self.response['result'])
        self.write_result()

    def base_reload(self, template, response):
        """
        Основная бизнес-логика замены полей
        :param template: шаблон (json)
        :param response: ответ (json)
        """
        record_types = ['record', 'recordset']
        # Заменяем структуру на актуальную
        self.reload_structure(template, response)
        # Далее итерируемся по "d" для замены рекордов
        for i in range(len(template['d'])):
            tmp_value = template['d'][i]
            resp_value = response['d'][i]
            if type(tmp_value) is dict and tmp_value.get('_type') in record_types:
                self.base_reload(tmp_value, resp_value)

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
        for i in range(len(resp_structure)):
            resp_matcher = resp_structure[i]
            tmp_matcher = tmp_structure[i] if i < len(tmp_structure) else None
            if resp_values:
                # Если recordset то value == все значения из массивов d
                value = [j[i] for j in resp_values] if template['_type'] == 'recordset' else resp_values[i]
            # Если поля одинаковые, итерируемся дальше
            if tmp_matcher == resp_matcher:
                continue
            # Поле добавилось
            if not tmp_matcher or resp_matcher not in tmp_structure:
                self.add_value(template, resp_matcher, value, i)
            # Поле удалили
            elif tmp_matcher and tmp_matcher not in resp_structure and resp_matcher in tmp_structure:
                self.delete_value(template, i)
            # Поле заменили
            elif tmp_matcher and tmp_matcher not in resp_structure and resp_matcher not in tmp_structure:
                self.replace_value(template, resp_matcher, value, i)
            # Поле переместилось
            elif tmp_matcher in resp_structure and resp_matcher in tmp_structure:
                self.delete_value(template, i)

        # Удалили последнии поля (итерируемся по "s" шаблона и чистим последние)
        if len(tmp_structure) > len(resp_structure):
            for i in range(len(resp_structure), len(tmp_structure)):
                template['s'].pop(i)
                template['d'].pop(i)

    @staticmethod
    def add_value(tmp, matcher_s, matcher_d, index):
        """Добавление поля"""
        tmp['s'].insert(index, matcher_s)
        if tmp['d']:
            if tmp['_type'] == 'recordset':
                for i in range(len(tmp['d'])):
                    tmp['d'][i].insert(index, matcher_d[i])
            else:
                tmp['d'].insert(index, matcher_d)

    @staticmethod
    def delete_value(tmp, index):
        """Удаление поля"""
        tmp['s'].pop(index)
        if tmp['d']:
            if tmp['_type'] == 'recordset':
                for i in range(len(tmp['d'])):
                    tmp['d'][i].pop(index)
            else:
                tmp['d'].pop(index)

    @staticmethod
    def replace_value(tmp, matcher_s, matcher_d, index):
        """Замена поля"""
        tmp['s'][index] = matcher_s
        if tmp['d']:
            if tmp['_type'] == 'recordset':
                for i in range(len(tmp['d'])):
                    tmp['d'][i][index] = matcher_d[i]
            else:
                tmp['d'][index] = matcher_d

    def write_result(self):
        """Запись готового шаблона в файл"""
        with open(self.tmp_path, 'w', encoding='UTF-8') as f:
            f.write(json.dumps(self.template, indent=3, ensure_ascii=False))
