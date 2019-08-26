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
setattr(User, 'scheduledrequests', db.relationship('ScheduledRequest', backref='author', lazy='dynamic'))


class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, index=True, nullable=False)
    args = db.Column(db.String, nullable=False)
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(64))
    task_id = db.Column(db.String(64), index=True, unique=True)
    error_message = db.Column(db.String(128))
    user_uuid = db.Column(db.String(36), db.ForeignKey('user.uuid'))
    scheduled_request_id = db.Column(db.Integer, db.ForeignKey('scheduled_request.id'))
    fileoutput = db.relationship("FileOutput", backref='request', cascade="delete", uselist=False)

    def __repr__(self):
        return "<Request(name='%s', submission date='%s', status='%s')" \
               % (self.name, self.submission_date, self.status)


class FileOutput(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(64), index=True, unique=True)
    size = db.Column(db.BigInteger)
    user_uuid = db.Column(db.String(36), db.ForeignKey('user.uuid'))
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'))

    def __repr__(self):
        return "<FileOutput(filename='%s', size='%s')" \
               % (self.filename, self.size)


class PeriodEnum(enum.Enum):
    days = 1
    hours = 2
    minutes = 3
    seconds = 4
    microseconds = 5


class ScheduledRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_uuid = db.Column(db.String(36), db.ForeignKey('user.uuid'))
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    args = db.Column(db.String)
    periodic_task = db.Column(db.Boolean)
    period = db.Column(db.Enum(PeriodEnum))
    every = db.Column(db.Integer)
    crontab_task = db.Column(db.Boolean)
    crontab_settings = db.Column(db.String(64))
    enabled = db.Column(db.Boolean)
    submitted_request = db.relationship('Request', backref='scheduled_request', lazy='dynamic')

    def __str__(self):
        return "db.%s(%s){%s}" \
               % (self.__class__.__name__, self.token, self.emitted_for)

    def __repr__(self):
        return self.__str__()
