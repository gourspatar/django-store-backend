from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0006_order_orderitem_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="stripe_session_id",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="order",
            name="stripe_payment_intent_id",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="order",
            name="paid_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
