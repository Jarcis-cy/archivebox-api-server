from rest_framework.decorators import api_view
from rest_framework.response import Response

from rest_framework import status

from . import service
from .serializers import AddUrlsSerializer
from drf_yasg.utils import swagger_auto_schema


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

            service.add_url(urls, tag, depth, update, update_all, overwrite, extractors, parser)

            return Response({'status': 'success'}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({'status': 'error', 'message': 'Invalid request method'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)
