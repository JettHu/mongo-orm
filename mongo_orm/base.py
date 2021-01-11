# -*- coding: utf-8 -*-
'''
# Created on Jan-07-21 12:18
# base.py
# @author: jetthu
# @email: jett.hux@gmail.com
'''
import logging
import bson

DEBUG = True
if DEBUG:
    logging.basicConfig(level=logging.DEBUG)


class MongoField:
    def __init__(self,
                 field_name,
                 field_type,
                 default,  # value or callable
                 pk,  # primary_key
                 required,    # field not empty
                 unique,
                 type_check,  # type check in save
                 validation,   # callable to validate value
                 **kwargs):
        if not isinstance(field_name, str):
            raise TypeError('field name is not a string')
        self.field_name = field_name    # database field name
        if not isinstance(field_type, type):
            raise TypeError('field type is not a python type')
        self.field_type = field_type  # database field type
        self.default = default  # value or callable
        self.pk = bool(pk)  # primary_key

        self.required = bool(required)
        self.unique = bool(unique)
        self.type_check = bool(type_check)
        self.validation = validation

    def __str__(self):
        return f'<{self.__class__.__name__}, {self.field_type}: {self.field_name}>'

    def validate(self, value, **kwargs):
        if self.type_check:
            if not isinstance(value, self.field_type):
                raise TypeError(f'value {repr(value)} is not a {self.field_type}')

        if self.validation:
            self.validation(value, **kwargs)


class CommonField(MongoField):
    def __init__(self, field_name, default=None,
                 required=False, unique=False, validation=None, **kw):
        super().__init__(
            field_name=field_name,
            default=default,
            required=required,
            unique=unique,
            validation=validation,
            field_type=type,
            type_check=False,
            pk=False,
            **kw,
        )


class StringField(MongoField):
    def __init__(self, field_name, default=None,
                 required=False, unique=False, type_check=False, validation=None):
        super().__init__(field_name, str, default, False, required, unique, type_check, validation)


class IntegerField(MongoField):
    def __init__(self, field_name, default=None,
                 required=False, unique=False, type_check=False, validation=None):
        super().__init__(field_name, int, default, False, required, unique, type_check, validation)


class BooleanField(MongoField):
    def __init__(self, field_name, default=None,
                 required=False, unique=False, type_check=False, validation=None):
        super().__init__(field_name, bool, default, False, required, unique, type_check, validation)


class FloatField(MongoField):
    def __init__(self, field_name, default=None,
                 required=False, unique=False, type_check=False, validation=None):
        super().__init__(field_name, float, default, False, required, unique, type_check, validation)


class _IdField(MongoField):
    def __init__(self):
        super().__init__('_id', bson.ObjectId, None, True, False, False, False, None)


class ModelMetaclass(type):
    def __new__(cls, name, base, attrs):
        # 排除Model基类
        if name == 'Model':
            return type.__new__(cls, name, base, attrs)
        table_name = attrs.get('__table__', None) or name.lower()
        logging.debug('found model: %s (table: %s)', name, table_name)
        mappings = dict()   # 类变量<=>列对象 映射关系
        fields = []
        pk = None   # 主键
        # 遍历类变量，将Field实例都放入mappings
        attrs['_id'] = _IdField()
        for k, v in attrs.items():
            if isinstance(v, MongoField):
                logging.debug('    found mapping: %s => %s', k, v)
                mappings[k] = v
                if v.pk:
                    if pk:
                        raise RuntimeError('Duplicate primary key for field: %s', k)
                    pk = k
                attrs[k] = v.default
            else:
                # 未定义的field类别
                fields.append(k)
            # attrs[k] = None
        if not pk:
            raise RuntimeError('Primary key not found.')
        # for k in mappings.keys():
        #     attrs.pop(k)
        attrs['__mappings__'] = mappings
        attrs['__table__'] = table_name
        attrs['__pk__'] = pk
        attrs['__fields__'] = fields
        attrs['__modified__'] = []
        return type.__new__(cls, name, base, attrs)


class Model(metaclass=ModelMetaclass):
    def __setattr__(self, key, value):
        if key in self.__mappings__:
            self.__mappings__[key].validate(value)
            self.__modified__.append(key)
        self.__dict__[key] = value

    # def get_value(self, key):
    #     return getattr(self, key, None)

    def get_value_or_default(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if not field.default:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s', key, value)
                setattr(self, key, value)
        return value

    def validate_fields(self):
        for name, field in self.__mappings__.items():
            field.validate(getattr(self, name, None))
        logging.debug('validate_fields passed')

    def save(self):
        self.validate_fields()
        if getattr(self, '_id', None):
            query = {'$set': {k: getattr(self, k) for k in self.__modified__}}
            logging.debug(f'update record _id={self._id}, {query}')
            self.__modified__.clear()
            return
        logging.debug(f'insert new record to collection {self.__table__}, {self}')
        self.__modified__.clear()

    def __str__(self):
        diction = {k: getattr(self, k, None) for k in self.__mappings__}
        if not diction['_id']:
            diction.pop('_id', None)
        return str(diction)
