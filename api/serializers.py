from rest_framework import serializers

from api.models import Result, Target, Tag, Tagging


class AddUrlsSerializer(serializers.Serializer):
    urls = serializers.ListField(
        child=serializers.URLField(),
        allow_empty=False,
        required=True,
        help_text="要添加的 URL 列表。例如：'https://example.com','https://example.org'"
    )
    tag = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        help_text="为添加的 URL 打上标签。"
    )
    depth = serializers.IntegerField(
        default=0,
        required=False,
        help_text="递归存档所有链接页面，深度为 0 或 1。",
        min_value=0,
        max_value=1
    )
    update = serializers.BooleanField(
        default=False,
        required=False,
        help_text="在添加新链接时重试之前跳过/失败的链接。"
    )
    update_all = serializers.BooleanField(
        default=False,
        required=False,
        help_text="在完成添加新链接后，更新索引中的所有链接。"
    )
    overwrite = serializers.BooleanField(
        default=False,
        required=False,
        help_text="从头开始重新存档 URL，覆盖任何现有文件。"
    )
    extractors = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            "title", "screenshot", "git", "favicon", "headers", "singlefile", "pdf", "dom", "wget", "readability",
            "mercury", "htmltotext", "media", "archive_org"
        ]),
        required=False,
        help_text="传递要使用的提取器列表，使用列表形式。例如：['title','screenshot','git']"
    )
    parser = serializers.ListField(
        child=serializers.ChoiceField(
            choices=['auto', 'pocket_api', 'readwise_reader_api', 'wallabag_atom', 'pocket_html', 'pinboard_rss',
                     'shaarli_rss', 'medium_rss', 'netscape_html', 'rss', 'json', 'jsonl', 'html', 'txt', 'url_list']),
        required=False,
        help_text="用于读取输入 URL 的解析器。",
    )

    @staticmethod
    def validate_extractors(value):
        if value:
            return ",".join(value)
        return ""

    @staticmethod
    def validate_parser(value):
        if value:
            return ",".join(value)
        return ""


class ResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Result
        fields = ['timestamp', 'status', 'output', 'extractor']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.status:
            return {
                'timestamp': representation['timestamp'],
                'status': representation['status'],
                'output': representation['output'],
                'extractor': representation['extractor']
            }
        else:
            return {
                'status': representation['status'],
                'timestamp': representation['timestamp'],
                'extractor': representation['extractor']
            }


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['name']


class TargetSerializer(serializers.ModelSerializer):
    results = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Target
        fields = ['url', 'domain', 'results', 'tags']

    def get_results(self, obj):
        results = Result.objects.filter(target_id=obj.id).order_by('-timestamp')
        sorted_results = sorted(
            results,
            key=lambda x: (not x.status, -x.timestamp)
        )
        extractors = self.context.get('extractors', [])
        if extractors:
            sorted_results = [result for result in sorted_results if result.extractor in extractors]
        return ResultSerializer(sorted_results, many=True).data

    @staticmethod
    def get_tags(obj):
        taggings = Tagging.objects.filter(target_id=obj.id).select_related('tag_id')
        return [tagging.tag_id.name for tagging in taggings]


class FilterTargetsSerializer(serializers.Serializer):
    tag_names = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        help_text="用于筛选目标的标签名称列表。"
    )
    domains = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        help_text="用于筛选目标的域名列表。"
    )
    urls = serializers.ListField(
        child=serializers.CharField(max_length=2000),
        required=False,
        help_text="用于筛选目标的URL列表。"
    )
    extractors = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            "title", "screenshot", "git", "favicon", "headers", "singlefile", "pdf", "dom", "wget", "readability",
            "mercury", "htmltotext", "media", "archive_org"
        ]),
        required=False,
        help_text="用于筛选提取器。"
    )
