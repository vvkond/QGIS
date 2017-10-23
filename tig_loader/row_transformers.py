from tig_loader.utils import Args, cached_property


class RowTransformer(Args):
    query = None


class Identity(RowTransformer):
    def create_transform_row(self, _context):
        def transform_row(input_row):
            yield input_row

        return transform_row


class FakeLob(object):
    def __init__(self, data):
        self.data = data

    def size(self):
        return len(self.data)

    def read(self, offset=1, amount=None):
        if amount is None:
            return self.data[offset - 1:]
        else:
            return self.data[offset - 1, offset - 1 + amount]


class BlobSplitter(RowTransformer):

    @cached_property
    def element_size(self):
        return int(self.args['element_size'])

    @cached_property
    def column_indexes(self):
        return map(int, self.args['columns'])

    @cached_property
    def create_fake_blob(self):
        return FakeLob

    def create_transform_row(self, _context):
        element_size = self.element_size
        column_indexes = self.column_indexes
        create_fake_blob = self.create_fake_blob

        def transform_row(input_row):
            min_blob_size = -1
            for column_index in column_indexes:
                blob = input_row[column_index]
                blob_size = blob.size()
                if min_blob_size == -1 or blob_size < min_blob_size:
                    min_blob_size = blob_size
            output_rows_count = min_blob_size // element_size
            if output_rows_count <= 0:
                return
            if output_rows_count == 1:
                yield input_row
                return
            fixed_min_blob_size = output_rows_count * element_size
            blob_datas = [None] * len(input_row)
            for column_index in column_indexes:
                blob = input_row[column_index]
                blob_datas[column_index] = blob.read(1, fixed_min_blob_size)
            output_row = list(input_row)
            offset = 0
            for _i in xrange(output_rows_count):
                next_offset = offset + element_size
                for column_index in column_indexes:
                    output_row[column_index] = create_fake_blob(blob_datas[column_index][offset:next_offset])
                yield tuple(output_row)
                offset = next_offset

        return transform_row


row_transformer_types = {
    'identity': Identity,
    'blob_splitter': BlobSplitter,
}


def create_row_transformer(args, **kw):
    return row_transformer_types[args['type']](args=args, **kw)
