from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_customuser_organization'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='account_no',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='customuser',
            name='bank',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
        migrations.AddField(
            model_name='customuser',
            name='account_name',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
    ]
