from mongo_orm import Model
from mongo_orm import StringField
from mongo_orm import CommonField

class User(Model):
    name = StringField('user_name', type_check=True)
    test_field = CommonField('test', default=-9999)
