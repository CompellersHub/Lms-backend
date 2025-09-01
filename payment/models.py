from django.db import models
from user.models import CustomUser
from courses.models import Course
from courses.mongo_utils import get_mongo_db

# Create your models here.

class Payment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    amount = models.DecimalField(decimal_places=2, max_digits=10)
    payment_method = models.CharField(max_length=100, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)

def __str__(self):
    return f"Payment of {self.amount} by {self.user.username} on {self.payment_date}"

db = get_mongo_db()

# bank_transfers = db['bank_transfers']
# bank_transfers.create_index("reference", unique=True)
# bank_transfers.create_index([("user_id", 1), ("course_id", 1)])
# bank_transfers.create_index("status")

# # Virtual account numbers mapped to users
# virtual_accounts = db['virtual_accounts']
# virtual_accounts.create_index("account_number", unique=True)