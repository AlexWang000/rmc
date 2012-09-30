from bson import json_util
import mongoengine as me
import redis

import rating
import rmc.shared.constants as c

# TODO(mack): remove this from here?
r = redis.StrictRedis(host=c.REDIS_HOST, port=c.REDIS_PORT, db=c.REDIS_DB)

import user_course


class Professor(me.Document):

    MIN_REVIEW_LENGTH = 15

    meta = {
        'indexes': [
            'clarity.rating',
            'clarity.count',
            'easiness.rating',
            'easiness.count',
            'passion.rating',
            'passion.count',
        ],
    }

    #FIXME(Sandy): Becker actually shows up as byron_becker
    # eg. byron_weber_becker
    id = me.StringField(primary_key=True)

    # TODO(mack): available in menlo data
    # department_id = me.StringField()

    # eg. Byron Weber
    first_name = me.StringField(required=True)

    # eg. Becker
    last_name = me.StringField(required=True)

    clarity = me.EmbeddedDocumentField(rating.AggregateRating, default=rating.AggregateRating())
    easiness = me.EmbeddedDocumentField(rating.AggregateRating, default=rating.AggregateRating())
    passion = me.EmbeddedDocumentField(rating.AggregateRating, default=rating.AggregateRating())

    @classmethod
    def get_id_from_name(cls, first_name, last_name=None):
        if last_name is None:
            return first_name.lower().replace(' ', '_')

        first_name = first_name.lower()
        last_name = last_name.lower()
        return ('%s %s' % (first_name, last_name)).replace(' ', '_')

    @staticmethod
    def guess_names(combined_name):
        """Returns first, last name given a string."""
        names = combined_name.split(' ')
        return (' '.join(names[:-1]), names[-1])

    @property
    def name(self):
        return '%s %s' % (self.first_name, self.last_name)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = Professor.get_id_from_name(self.first_name, self.last_name)

        super(Professor, self).save(*args, **kwargs)

    def get_ratings(self):
        ratings_dict = {
            'clarity': self.clarity,
            'easiness': self.easiness,
            'passion': self.passion,
        }
        ratings_dict['overall'] = rating.get_overall_rating(
                ratings_dict.values())
        return ratings_dict

    # TODO(david): This should go on ProfCourse
    def get_ratings_for_course(self, course_id):
        rating_dict = {}
        for name in ['clarity', 'easiness', 'passion']:
            rating_json = r.get(':'.join([course_id, self.id, name]))
            if rating_json:
                rating_loaded = json_util.loads(rating_json)
                rating_dict[name] = rating.AggregateRating(
                    rating=rating_loaded['rating'],
                    count=rating_loaded['count'],
                )

        rating_dict['overall'] = rating.get_overall_rating(
                rating_dict.values())

        return rating_dict
