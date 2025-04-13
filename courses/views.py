from django.shortcuts import redirect, render
from rest_framework import status
from .models import *
from .serializer import *
from user.models import CustomUser
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings

# Create your views here.

PAYPAD_API_KEY = "your_paypad_api_key"  # Replace with your actual Paypad API Key
PAYPAD_BASE_URL = "https://paypad.com/api/v1"  # Adjust if Paypad has a different base URL

def initiate_paypad_payment(request, order_id):
    order = get_object_or_404(CourseOrder, id=order_id, user=request.user)

    # Paypad Payment Data
    payload = {
        "amount": order.total_price,
        "currency": "NGN",  # Change if using a different currency
        "reference": f"order-{order.id}",
        "callback_url": f"{settings.SITE_URL}/paypad/callback/",
        "customer": {
            "email": request.user.email,
            "name": request.user.get_full_name(),
        }
    }

    headers = {
        "Authorization": f"Bearer {PAYPAD_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(f"{PAYPAD_BASE_URL}/payments", json=payload, headers=headers)

    if response.status_code == 200:
        data = response.json()
        order.paypad_reference = data.get("reference")
        order.save()
        return redirect(data.get("payment_url"))  # Redirect user to Paypad payment page

    return JsonResponse({"error": "Payment initiation failed"}, status=400)


@csrf_exempt
def paypad_callback(request):
    if request.method == "POST":
        data = request.POST  # Assuming Paypad sends POST data
        reference = data.get("reference")
        status = data.get("status")

        order = CourseOrder.objects.filter(paypad_reference=reference).first()

        if order:
            if status == "success":
                order.payment_status = "paid"
                order.save()
                return JsonResponse({"message": "Payment successful"}, status=200)
            else:
                order.payment_status = "failed"
                order.save()
                return JsonResponse({"message": "Payment failed"}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def create_course_order(request):
    if request.method == "POST":
        user = request.user
        course_ids = request.POST.getlist('course_ids[]')

        if not course_ids:
            return JsonResponse({"error": "No courses selected"}, status=400)

        order = CourseOrder.objects.create(user=user, total_price=0)

        total_price = 0
        for course_id in course_ids:
            course = get_object_or_404(Course, id=course_id)
            total_price += course.price 

            CourseOrderItem.objects.create(order=order, course=course, price=course.price)

        order.total_price = total_price
        order.save()

        return JsonResponse({"message": "Order created successfully", "order_id": order.id})
    return JsonResponse({"error": "Invalid request"}, status=400)

class Courses(APIView):
    # permission_classes = [IsAuthenticated]
    def get(self, request):
        courses = Course.objects.all()
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
    def get(self, request, pk):
        course = Course.objects.get(id=pk)
        serializer = CourseSerializer(course)
        return Response(serializer.data)
    
    
    def put(self, request, pk):
        course = Course.objects.get(id=pk)
        serializer = CourseSerializer(instance=course, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        course = Course.objects.get(id=pk)
        course.delete()
        return Response({'message': 'Course deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
    
class Categories(APIView):
    
    def get(self, request):
        categories = Category.objects.all()
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
        try:
            category = Category.objects.get(id=pk)
            course = Course.objects.filter(category=category)
            serializer = CourseSerializer(course, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Category.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)



class CourseOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get all Course Orders for the authenticated user"""
        orders = CourseOrder.objects.filter(user=request.user)
        serializer = CourseOrderSerializer(orders, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create a Course Order"""
        course_ids = request.data.get('course_ids', [])
        
        if not course_ids:
            return Response({"error": "No courses selected"}, status=status.HTTP_400_BAD_REQUEST)

        total_price = 0
        order = CourseOrder.objects.create(user=request.user, total_price=0)

        for course_id in course_ids:
            course = get_object_or_404(Course, id=course_id)
            total_price += course.price
            CourseOrderItem.objects.create(order=order, course=course, price=course.price)

        order.total_price = total_price
        order.save()

        return Response(CourseOrderSerializer(order).data, status=status.HTTP_201_CREATED)

class CourseOrderDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        """Retrieve a single order by ID"""
        order = get_object_or_404(CourseOrder, id=order_id, user=request.user)
        serializer = CourseOrderSerializer(order)
        return Response(serializer.data)

class CourseOrderItemAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        """Retrieve all items for a specific order"""
        order = get_object_or_404(CourseOrder, id=order_id, user=request.user)
        items = CourseOrderItem.objects.filter(order=order)
        serializer = CourseOrderItemSerializer(items, many=True)
        return Response(serializer.data)

class Assignment(APIView):
    def get(self, request, order_id):
        assignment = Assignment.objects.all()
        serializer = AssignmentSerializer(assignment, many=True)
        return Response(serializer.data)


class AssignmentDetail(APIView):
    def get(self, request, pk):
        assignment = Assignment.objects.get(id=pk)
        serializer = AssignmentSerializer(assignment)
        return Response(serializer.data)
    
    def put(self, request, pk):
        assignment = Assignment.objects.get(id=pk)
        serializer = AssignmentSerializer(instance=assignment, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        assignment = Assignment.objects.get(id=pk)
        assignment.delete()
        return Response({'message': 'Assignment deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

class AssignmentByCourse(APIView):
    def get(self, request, pk):
        try:
            assignment = Assignment.objects.get(id=pk)
            course = Course.objects.filter(assignment=assignment)
            serializer = AssignmentSerializer(course, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except assignment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class AssignmentSubmission(APIView):
    def get(self, request):
        assignment_submission = Submission.objects.all()
        serializer = SubmissionSerializer(assignment_submission, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = SubmissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 
    
class AssignmentSubmissionDetail(APIView):
    def get(self, request, pk):
        assignment_submission = Submission.objects.get(id=pk)
        serializer = SubmissionSerializer(assignment_submission)
        return Response(serializer.data)
    
    def put(self, request, pk):
        assignment_submission = Submission.objects.get(id=pk)
        serializer = SubmissionSerializer(instance=assignment_submission, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        assignment_submission = Submission.objects.get(id=pk)
        assignment_submission.delete()
        return Response({'message': 'Assignment submission deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
    
class AssignmentSubmissionByUser(APIView):
    def get(self,request, pk):
        assignment_submission = Submission.objects.all(id=pk)
        user = CustomUser.objects.filter(assignment_submission=assignment_submission)
        serializer = SubmissionSerializer(user, many=True)
        return Response(serializer.data)
    