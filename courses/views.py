from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from bson.objectid import ObjectId
from datetime import datetime
from .serializer import (
    CategorySerializer,
    CourseSerializer,
    CourseOrderSerializer,
    CourseOrderItemSerializer,
    AssignmentSerializer,
    SubmissionSerializer,
    VideoSerializer,
    ModuleSerializer,
)
from .mongo_utils import get_mongo_db

# PAYPAD_API_KEY = "your_paypad_api_key"  # Replace with your actual Paypad API Key
# PAYPAD_BASE_URL = "https://paypad.com/api/v1"  # Adjust if Paypad has a different base URL

# @login_required
# def create_course_order(request):
#     if request.method == "POST":
#         db = get_mongo_db()
#         user_id = str(request.user.id)  # Assuming you store Django user ID as string in MongoDB

#         course_ids = request.POST.getlist('course_ids[]')

#         if not course_ids:
#             return JsonResponse({"error": "No courses selected"}, status=400)

#         total_price = 0
#         order_data = {
#             "user_id": user_id,
#             "total_price": 0,
#             "payment_status": "pending",
#             "created_at": datetime.utcnow(),
#             "updated_at": datetime.utcnow(),
#             "order_items": []
#         }
#         order_result = db.course_orders.insert_one(order_data)
#         order_id = str(order_result.inserted_id)

#         for course_id in course_ids:
#             course = db.courses.find_one({"_id": ObjectId(course_id)})
#             if course:
#                 total_price += course.get('price', 0)
#                 item_data = {
#                     "order_id": order_id,
#                     "course_id": course_id,
#                     "price": course.get('price', 0)
#                 }
#                 db.course_order_items.insert_one(item_data)

#         db.course_orders.update_one({"_id": ObjectId(order_id)}, {"$set": {"total_price": total_price}})

#         return JsonResponse({"message": "Order created successfully", "order_id": order_id})
#     return JsonResponse({"error": "Invalid request"}, status=400)

# def initiate_paypad_payment(request, order_id):
#     db = get_mongo_db()
#     order = db.course_orders.find_one({"_id": ObjectId(order_id), "user_id": str(request.user.id)})

#     if not order:
#         return JsonResponse({"error": "Order not found"}, status=404)

#     payload = {
#         "amount": order.get("total_price", 0),
#         "currency": "NGN",  # Change if using a different currency
#         "reference": f"order-{order_id}",
#         "callback_url": f"{settings.SITE_URL}/paypad/callback/",
#         "customer": {
#             "email": request.user.email,
#             "name": request.user.get_full_name(),
#         }
#     }

#     headers = {
#         "Authorization": f"Bearer {PAYPAD_API_KEY}",
#         "Content-Type": "application/json"
#     }

#     response = requests.post(f"{PAYPAD_BASE_URL}/payments", json=payload, headers=headers)

#     if response.status_code == 200:
#         data = response.json()
#         db.course_orders.update_one({"_id": ObjectId(order_id)}, {"$set": {"paypad_reference": data.get("reference")}})
#         return redirect(data.get("payment_url"))  # Redirect user to Paypad payment page

#     return JsonResponse({"error": "Payment initiation failed"}, status=400)

# @csrf_exempt
# def paypad_callback(request):
#     if request.method == "POST":
#         db = get_mongo_db()
#         data = request.POST  # Assuming Paypad sends POST data
#         reference = data.get("reference")
#         status = data.get("status")

#         order = db.course_orders.find_one({"paypad_reference": reference})

#         if order:
#             if status == "success":
#                 db.course_orders.update_one({"_id": order["_id"]}, {"$set": {"payment_status": "paid"}})
#                 return JsonResponse({"message": "Payment successful"}, status=200)
#             else:
#                 db.course_orders.update_one({"_id": order["_id"]}, {"$set": {"payment_status": "failed"}})
#                 return JsonResponse({"message": "Payment failed"}, status=400)

#     return JsonResponse({"error": "Invalid request"}, status=400)

class Courses(APIView):
    # permission_classes = [IsAuthenticated]
    def get(self, request):
        db = get_mongo_db()
        courses = list(db.courses.find())
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CourseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CourseDetail(APIView):
    permission_classes = [IsAuthenticated]
    def get_object(self, pk):
        db = get_mongo_db()
        try:
            return db.courses.find_one({"_id": ObjectId(pk)})
        except:
            return None

    def get(self, request, pk):
        course = self.get_object(pk)
        if course:
            serializer = CourseSerializer(course)
            return Response(serializer.data)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        course = self.get_object(pk)
        if course:
            serializer = CourseSerializer(instance=course, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        db = get_mongo_db()
        course = self.get_object(pk)
        if course:
            db.courses.delete_one({"_id": ObjectId(pk)})
            return Response({'message': 'Course deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_404_NOT_FOUND)

class Categories(APIView):

    def get(self, request):
        db = get_mongo_db()
        categories = list(db.categories.find())
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CoursesByCategory(APIView):
    def get(self, request, pk):
        db = get_mongo_db()
        try:
            category = db.categories.find_one({"_id": ObjectId(pk)})
            if category:
                courses = list(db.courses.find({"category_id": str(category['_id'])}))
                serializer = CourseSerializer(courses, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(status=status.HTTP_404_NOT_FOUND)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

class CourseOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        db = get_mongo_db()
        orders = list(db.course_orders.find({"user_id": str(request.user.id)}))
        serializer = CourseOrderSerializer(orders, many=True)
        return Response(serializer.data)

    def post(self, request):
        db = get_mongo_db()
        course_ids = request.data.get('course_ids', [])

        if not course_ids:
            return Response({"error": "No courses selected"}, status=status.HTTP_400_BAD_REQUEST)

        total_price = 0
        order_data = {
            "user_id": str(request.user.id),
            "total_price": 0,
            "payment_status": "pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "order_items": []
        }
        order_result = db.course_orders.insert_one(order_data)
        order_id = str(order_result.inserted_id)

        order_item_data = []
        for course_id in course_ids:
            course = db.courses.find_one({"_id": ObjectId(course_id)})
            if course:
                total_price += course.get('price', 0)
                item_data = {
                    "order_id": order_id,
                    "course_id": course_id,
                    "price": course.get('price', 0)
                }
                order_item_data.append(item_data)

        if order_item_data:
            db.course_order_items.insert_many(order_item_data)
            db.course_orders.update_one({"_id": ObjectId(order_id)}, {"$set": {"total_price": total_price}})

        order = db.course_orders.find_one({"_id": ObjectId(order_id)})
        serializer = CourseOrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class CourseOrderDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        db = get_mongo_db()
        order = db.course_orders.find_one({"_id": ObjectId(order_id), "user_id": str(request.user.id)})
        if order:
            serializer = CourseOrderSerializer(order)
            return Response(serializer.data)
        return Response(status=status.HTTP_404_NOT_FOUND)

class CourseOrderItemAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        db = get_mongo_db()
        items = list(db.course_order_items.find({"order_id": order_id}))
        serializer = CourseOrderItemSerializer(items, many=True)
        return Response(serializer.data)

class Assignment(APIView):
    def get(self, request):
        db = get_mongo_db()
        assignments = list(db.assignments.find())
        serializer = AssignmentSerializer(assignments, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = AssignmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AssignmentDetail(APIView):
    def get_object(self, pk):
        db = get_mongo_db()
        try:
            return db.assignments.find_one({"_id": ObjectId(pk)})
        except:
            return None

    def get(self, request, pk):
        assignment = self.get_object(pk)
        if assignment:
            serializer = AssignmentSerializer(assignment)
            return Response(serializer.data)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        assignment = self.get_object(pk)
        if assignment:
            serializer = AssignmentSerializer(instance=assignment, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        db = get_mongo_db()
        assignment = self.get_object(pk)
        if assignment:
            db.assignments.delete_one({"_id": ObjectId(pk)})
            return Response({'message': 'Assignment deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_404_NOT_FOUND)

class AssignmentByCourse(APIView):
    def get(self, request, pk):
        db = get_mongo_db()
        try:
            # Assuming 'course_id' in Assignment refers to the Course _id as a string
            assignments = list(db.assignments.find({"course_id": pk}))
            serializer = AssignmentSerializer(assignments, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

class AssignmentSubmission(APIView):
    def get(self, request):
        db = get_mongo_db()
        submissions = list(db.submissions.find())
        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = SubmissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AssignmentSubmissionDetail(APIView):
    def get_object(self, pk):
        db = get_mongo_db()
        try:
            return db.submissions.find_one({"_id": ObjectId(pk)})
        except:
            return None

    def get(self, request, pk):
        submission = self.get_object(pk)
        if submission:
            serializer = SubmissionSerializer(submission)
            return Response(serializer.data)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        submission = self.get_object(pk)
        if submission:
            serializer = SubmissionSerializer(instance=submission, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        db = get_mongo_db()
        submission = self.get_object(pk)
        if submission:
            db.submissions.delete_one({"_id": ObjectId(pk)})
            return Response({'message': 'Assignment submission deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_404_NOT_FOUND)

class AssignmentSubmissionByUser(APIView):
    def get(self, request, user_id): # Changed 'pk' to 'user_id' for clarity
        db = get_mongo_db()
        submissions = list(db.submissions.find({"user_id": user_id})) # Assuming 'user_id' field in submissions
        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

class Module(APIView):
    def get(self, request):
        db = get_mongo_db()
        modules = list(db.modules.find())
        serializer = ModuleSerializer(modules, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ModuleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ModuleByCourse(APIView):
    def get(self, request, course_id):
        db = get_mongo_db()
        modules = list(db.modules.find({"course_id": course_id}))
        serializer = ModuleSerializer(modules, many=True)
        return Response(serializer.data)

class ModuleDetail(APIView):
    def get_object(self, pk):
        db = get_mongo_db()
        try:
            return db.modules.find_one({"_id": ObjectId(pk)})
        except:
            return None

    def get(self, request, pk):
        module = self.get_object(pk)
        if module:
            serializer = ModuleSerializer(module)
            return Response(serializer.data)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        module = self.get_object(pk)
        if module:
            serializer = ModuleSerializer(instance=module, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        db = get_mongo_db()
        module = self.get_object(pk)
        if module:
            db.modules.delete_one({"_id": ObjectId(pk)})
            return Response({'message': 'Module deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_404_NOT_FOUND)

class Video(APIView):
    def get(self, request):
        db = get_mongo_db()
        videos = list(db.videos.find())
        serializer = VideoSerializer(videos, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = VideoSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class VideoByModule(APIView):
    def get(self, request, module_id):
        db = get_mongo_db()
        videos = list(db.videos.find({"module_id": module_id}))
        serializer = VideoSerializer(videos, many=True)
        return Response(serializer.data)


class VideoDetail(APIView):
    def get_object(self, pk):
        db = get_mongo_db()
        try:
            return db.videos.find_one({"_id": ObjectId(pk)})
        except:
            return None

    def get(self, request, pk):
        video = self.get_object(pk)
        if video:
            serializer = VideoSerializer(video)
            return Response(serializer.data)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        video = self.get_object(pk)
        if video:
            serializer = VideoSerializer(instance=video, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        db = get_mongo_db()
        video = self.get_object(pk)
        if video:
            db.videos.delete_one({"_id": ObjectId(pk)})
            return Response({'message': 'Video deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_404_NOT_FOUND)