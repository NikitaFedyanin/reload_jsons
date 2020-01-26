from helpers import *

client = Client()
client.reload_template('asserts/template.json')
client.compare_jsons('asserts/template.json')

# client.reload_template('asserts/template.json')
