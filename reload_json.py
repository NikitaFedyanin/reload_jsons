import json


class ReloadJson:
    template = None
    response = None

    def __init__(self, template, response):
        self.template = json.loads(template)
        self.response = json.loads(response)

    def reload(self):
        self.reload_structure()

    def reload_structure(self):
        tmp_structure = self.template['result']['s']
        resp_structure = self.response['result']['s']
        for i in range(len(tmp_structure)):
            tmp_matcher = tmp_structure[i]
            resp_matcher = resp_structure[i]
            # Если поля одинаковые, итерируемся дальше
            if tmp_matcher == resp_matcher:
                continue
            # Поле добавилось
            if resp_matcher in
