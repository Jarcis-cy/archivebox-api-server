from rest_framework.decorators import api_view
from rest_framework.response import Response

from rest_framework import status

from . import service
from .serializers import AddUrlsSerializer, FilterTargetsSerializer
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


@swagger_auto_schema(method='post', request_body=AddUrlsSerializer)
@api_view(['POST'])
def add_urls(request):
    if request.method == 'POST':
        serializer = AddUrlsSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            urls = data.get('urls')
            tag = data.get('tag')
            depth = data.get('depth', 0)
            update = data.get('update', False)
            update_all = data.get('update_all', False)
            overwrite = data.get('overwrite', False)
            extractors = data.get('extractors')
            parser = data.get('parser', 'auto')

            result = service.add_url(urls, tag, depth, update, update_all, overwrite, extractors, parser)

            if result["status"] == "success":
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
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


@swagger_auto_schema(method='post', request_body=FilterTargetsSerializer)
@api_view(['POST'])
def list_target(request):
    if request.method == 'POST':
        serializer = FilterTargetsSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            result = filter_targets(data)

            if result["status"] == "success":
                return Response(result, status=status.HTTP_200_OK)
            elif result["status"] == "partial_success":
                return Response(result, status=status.HTTP_206_PARTIAL_CONTENT)
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({'status': 'error', 'message': 'Invalid request method'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
