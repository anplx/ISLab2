#!/usr/bin/env python2

import sqlite3
from flask import Flask, request, jsonify
from peewee import *
DB_PATH = './posts.db'
PORT    = 4001

app = Flask(__name__)
global storage
storage = None



db = SqliteDatabase(DB_PATH)
class Shablon(Model):
    class Meta:
        database=db

class Posts(Shablon):
    pid=AutoField()  
    post_id=IntegerField()
    title=TextField()
    content=TextField()
    token=TextField()

    class Meta:
        table_name='posts'

class Posts_Total(Shablon):
    pid=AutoField() 
    type=TextField()
    value=IntegerField()

    class Meta:
        table_name = 'posts_total'


class Storage:
    def __init__(self, db_path):
        self.db_path = db_path
        self.priv_edge, self.pub_edge = self._get_posts_edges()

    def _get_posts_edges(self):

        query = Posts_Total.select(Posts_Total.value).where((Posts_Total.type == "private") | (Posts_Total.type == "public"))

        try:
            priv = int(query[0].value)
            pub = int(query[1].value)

        except:
            priv, pub = 1, 1
            query = Posts_Total.insert({Posts_Total.type: 'private', Posts_Total.value: priv}).execute()
            query = Posts_Total.insert({Posts_Total.type: 'public', Posts_Total.value: pub}).execute()

        return priv, pub

    def _inc_posts_edge(self, edge_id):
        assert edge_id in ['private', 'public']

        if edge_id == 'private':
            self.priv_edge+= 1
            new_val = self.priv_edge
        else:
            self.pub_edge+= 1
            new_val = self.pub_edge

        query = Posts_Total.update({Posts_Total.value: new_val}).where(Posts_Total.type == edge_id).execute()

    def get_private_post(self, post_id, token):
        query = Posts.select(Posts.token).where(Posts.post_id == post_id)
        stoken = query[0].token
        if stoken != token:
            return None

        return self._get_post(post_id)

    def get_public_post(self, post_id):
        return self._get_post(post_id)

    def _get_post(self, post_id):
        query = Posts.select(Posts.title, Posts.content).where(Posts.post_id == post_id)
        post = query[0]
        if post is None:
            return None

        return {'title': post.title, 'content': post.content}

    def store_public_post(self, title, content):
        self._store_post(self.pub_edge, title, content)
        self._inc_posts_edge('public')

        return self.pub_edge - 1

    def store_private_post(self, title, content, token):
        self._store_post(-self.priv_edge, title, content, token)
        self._inc_posts_edge('private')

        return -(self.priv_edge - 1)

    def _store_post(self, post_id, title, content, token=''):
        query = Posts.insert({Posts.post_id: post_id, Posts.title: title, Posts.content: content, Posts.token: token}).execute()


@app.route('/get', methods=['GET'])
def get_post():
    global storage
    result_json = dict()

    if request.is_json:
        print request.json
        try:
            post_id = request.json['post_id']
            if post_id > 0:
                res = storage.get_public_post(post_id)

            elif post_id < 0:
                token = request.json['token']
                res = storage.get_private_post(post_id, token)

            else:
                result_json['status']   = 'error'
                result_json['data']     = 'Are you dumb or wut?'
                return result_json

            if res is None:
                result_json['status']   = 'error'
                result_json['data']     = 'No posts with such post_id or your token is incorrect'
            else:
                result_json['status']   = 'success'
                result_json['data']     = res

        except KeyError:
            result_json['status']   = 'error'
            result_json['data']     = 'Missing fields in JSON'

        except Exception as e:
            raise e
            result_json['status'] = 'error'
            result_json['data']   = 'An error occured on server side'

    else:
        result_json['status']   = 'error'
        result_json['data']     = 'Request isn\'t in JSON format'

    print result_json
    return jsonify(result_json)


@app.route('/store', methods = ['POST'])
def store_post():
    global storage
    result_json = dict()

    if request.is_json:
        try:
            title   = request.json['title']
            content = request.json['content']
            public  = request.json['public']

            if public:
                post_id = storage.store_public_post(title, content)

            else:
                token = request.json['token']
                post_id = storage.store_private_post(title, content, token)

            result_json['status'] = 'success'
            result_json['data']   = {'post_id': post_id}

        except KeyError as e:
            result_json['status']   = 'error'
            result_json['data']     = 'Missing fields in JSON'

        except Exception as e:
            raise e
            result_json['status'] = 'error'
            result_json['data']   = 'An error occured on server side'

    else:
        result_json['status']   = 'error'
        result_json['data']     = 'Request isn\'t in JSON format'

    print result_json
    return jsonify(result_json)

@app.before_request
def before_request():
    db.connect()

@app.after_request
def after_request(response):
    db.close()
    return response


if __name__ == '__main__':
    with db:
        db.create_tables([Posts, Posts_Total])

    global storage
    storage = Storage(DB_PATH)

    app.run(host='0.0.0.0', port=PORT, debug=True)

