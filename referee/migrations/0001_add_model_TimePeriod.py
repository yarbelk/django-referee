# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'TimePeriod'
        db.create_table(u'referee_timeperiod', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('period_start', self.gf('django.db.models.fields.DateTimeField')()),
            ('period_end', self.gf('django.db.models.fields.DateTimeField')(null=True)),
        ))
        db.send_create_signal(u'referee', ['TimePeriod'])


    def backwards(self, orm):
        # Deleting model 'TimePeriod'
        db.delete_table(u'referee_timeperiod')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'referee.claim': {
            'Meta': {'object_name': 'Claim'},
            'claim_confirmed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'claim_confirmed_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'fan': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'claimed'", 'to': u"orm['referee.Participant']"}),
            'gift': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'all_claims'", 'to': u"orm['referee.Prize']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question1': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'question2': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'question3': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'question4': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'time_period': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'+'", 'to': u"orm['referee.TimePeriod']"}),
            'unclaimed_at': ('django.db.models.fields.DateTimeField', [], {}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'referee.participant': {
            'Meta': {'object_name': 'Participant'},
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '50'}),
            'extra_spins_received': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'finish_quiz': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'full_name': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_spin': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'nric': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'spin_times': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "u'+'", 'unique': 'True', 'to': u"orm['auth.User']"})
        },
        u'referee.prize': {
            'Meta': {'object_name': 'Prize'},
            'css_class': ('django.db.models.fields.CharField', [], {'max_length': '15'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slice_no': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'time_periods': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "u'prizes'", 'symmetrical': 'False', 'through': u"orm['referee.TimePeriodPrizeAvailable']", 'to': u"orm['referee.TimePeriod']"}),
            'total_units': ('django.db.models.fields.IntegerField', [], {'default': '3'})
        },
        u'referee.timeperiod': {
            'Meta': {'ordering': "(u'-period_start',)", 'unique_together': "((u'period_start', u'period_end'),)", 'object_name': 'TimePeriod'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'period_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'period_start': ('django.db.models.fields.DateTimeField', [], {})
        },
        u'referee.timeperiodprizeavailable': {
            'Meta': {'unique_together': "((u'time_period', u'prize'),)", 'object_name': 'TimePeriodPrizeAvailable'},
            'all_claimed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'prize': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'time_period_won'", 'to': u"orm['referee.Prize']"}),
            'time_period': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'+'", 'to': u"orm['referee.TimePeriod']"})
        }
    }

    complete_apps = ['referee']