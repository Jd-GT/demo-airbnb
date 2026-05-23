from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_emailtemplate'),
    ]

    operations = [
        migrations.AddField(
            model_name='googlecalendarcredential',
            name='google_account_email',
            field=models.EmailField(blank=True, max_length=254),
        ),
    ]
