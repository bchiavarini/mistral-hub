# -*- coding: utf-8 -*-

""" CUSTOM Models for the relational database """

from restapi.models.sqlalchemy import db, User
from datetime import datetime

import enum

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Add (inject) attributes to User
setattr(User, 'my_custom_field', db.Column(db.String(255)))

setattr(User, 'requests', db.relationship('Request', backref='author', lazy='dynamic'))
setattr(User, 'fileoutput', db.relationship('FileOutput', backref='owner', lazy='dynamic'))
setattr(User, 'scheduledrequest', db.relationship('ScheduledRequest', backref='author', lazy='dynamic'))



class Request (db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    args = db.Column(db.String)
    status = db.Column(db.String(64))
    task_id = db.Column(db.String(64), index=True, unique=True)
    fileoutput = db.relationship("FileOutput", backref='request', uselist=False)

    def __str__(self):
        return "db.%s(%s){%s}" \
            % (self.__class__.__name__, self.token, self.emitted_for)

    def __repr__(self):
        return self.__str__()

class FileOutput (db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(64), index=True, unique=True)
    size = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'))

    def __str__(self):
        return "db.%s(%s){%s}" \
            % (self.__class__.__name__, self.token, self.emitted_for)

    def __repr__(self):
        return self.__str__()

class PeriodEnum(enum.Enum):
    days = 1
    hours = 2
    minutes = 3
    seconds = 4
    microseconds = 5


class ScheduledRequest (db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    args = db.Column(db.String)
    periodic_task = db.Column(db.Boolean)
    periode = db.Column(db.Enum(PeriodEnum))
    every = db.Column(db.Integer)
    cronjob_task = db.Column(db.Boolean)
    cronjob_settings = db.Column(db.String(64))

    def __str__(self):
        return "db.%s(%s){%s}" \
            % (self.__class__.__name__, self.token, self.emitted_for)

    def __repr__(self):
        return self.__str__()
