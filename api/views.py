from drf_yasg import openapi
from rest_framework.decorators import api_view
from rest_framework.response import Response

from rest_framework import status

from . import service
from .serializers import AddUrlsSerializer, FilterTargetsSerializer, SuccessResponseSerializer, \
    PartialSuccessResponseSerializer, ErrorResponseSerializer, common_responses
from drf_yasg.utils import swagger_auto_schema

from .service import filter_targets


@api_view(['GET'])
def init_project(request):
    if request.method == 'GET':
        result = service.initialize_archivebox()

        if result["status"] == "success":
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response({'status': 'error', 'message': 'Invalid request method'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)


@swagger_auto_schema(method='post', request_body=AddUrlsSerializer, responses=common_responses)
@api_view(['POST'])
def add_urls(request):
    if request.method == 'POST':
        serializer = AddUrlsSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            result = service.add_url(
                data.get('urls'),
                data.get('tag'),
                data.get('depth', 0),
                data.get('update', False),
                data.get('update_all', False),
                data.get('overwrite', False),
                data.get('extractors'),
                data.get('parser', 'auto')
            )
            return handle_response(result)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({'status': 'error', 'message': 'Invalid request method'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)


@api_view(['GET'])
def synchronization(request):
    if request.method == 'GET':
        result = service.synchronize_local_data()

        if result["status"] == "success":
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response({'status': 'error', 'message': 'Invalid request method'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)


@swagger_auto_schema(method='post', request_body=FilterTargetsSerializer, responses=common_responses)
@api_view(['POST'])
def list_target(request):
    if request.method == 'POST':
        serializer = FilterTargetsSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            result = filter_targets(data)
            return handle_response(result)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({'status': 'error', 'message': 'Invalid request method'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)


def handle_response(result):
    if result["status"] == "success":
        return Response(result, status=status.HTTP_200_OK)
    elif result["status"] == "partial_success":
        return Response(result, status=status.HTTP_207_MULTI_STATUS)
    else:
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
