import json
from copy import deepcopy


class ReloadJson:
    template = None
    response = None

    def __init__(self, template, response):
        self.template = json.loads(template)
        self.response = json.loads(response)
        self.base_reload(self.template['result'], self.response['result'])
        self.write_result()

    def base_reload(self, template, response):
        self.reload_structure(template, response)
        # Далее итерируемся по "d" для замены рекордов
        for i in range(len(template['d'])):
            tmp_value = template['d'][i]
            resp_value = response['d'][i]
            if type(tmp_value) is dict and tmp_value.get('_type') == 'record':
                self.base_reload(tmp_value, resp_value)

    def reload_structure(self, template, response):
        tmp_structure = template['s']
        resp_structure = response['s']
        resp_values = response['d']
        for i in range(len(resp_structure)):
            resp_matcher = resp_structure[i]
            tmp_matcher = tmp_structure[i] if i < len(tmp_structure) else None
            # Если поля одинаковые, итерируемся дальше
            if tmp_matcher == resp_matcher:
                continue
            # Поле добавилось
            if not tmp_matcher or resp_matcher not in tmp_structure:
                self.add_value(template, resp_matcher, resp_values[i], i)
            # Поле удалили
            if tmp_matcher and tmp_matcher not in resp_structure and resp_matcher in tmp_structure:
                self.delete_value(template, i)
            # Поле заменили
            if tmp_matcher and tmp_matcher not in resp_structure and resp_matcher not in tmp_structure:
                self.replace_value(template, resp_matcher, resp_values[i], i)

    @staticmethod
    def add_value(tmp, matcher_s, matcher_d, index):
        tmp['s'].insert(index, matcher_s)
        tmp['d'].insert(index, matcher_d)

    @staticmethod
    def delete_value(tmp, index):
        tmp['s'].pop(index)
        tmp['d'].pop(index)

    @staticmethod
    def replace_value(tmp, matcher_s, matcher_d, index):
        tmp['s'][index] = matcher_s
        tmp['d'][index] = matcher_d

    def write_result(self):
        with open('asserts/template.json', 'w', encoding='UTF-8') as f:
            f.write(json.dumps(self.template, indent=3, ensure_ascii=False))
