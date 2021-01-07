from mongo_orm import Model
from mongo_orm import StringField

class User(Model):
    name = StringField('user_name', type_check=True)
