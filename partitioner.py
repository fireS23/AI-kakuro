class Partitioner:
    @staticmethod
    def partition(N, k, growing_list=[]):
        partitions = []

        if k == 0:
            return partitions
        if k == 1:
            if N <= 0:
                return partitions
            if N <= 9:
                return [[*growing_list, N]]
            return partitions

        for i in range(1, 10):  # 'i' is from 1 to 9
            r = N - i
            if r <= 0:
                break
            if r / (k - 1) > 9:
                continue  # Skipping calculation of impossible partitions
            partitions += Partitioner.partition(r, k - 1, growing_list + [i])

        return partitions

    @staticmethod
    def remove_duplicates(partition_list):
        partitions = partition_list.copy()
        i = 0
        while i < len(partitions):
            if len(partitions[i]) != len(set(partitions[i])):
                partitions.pop(i)
            else:
                i += 1
        return partitions

    @staticmethod
    def get_ordered_partitions(N, k) -> list:
        return Partitioner.remove_duplicates(Partitioner.partition(N, k))

    @staticmethod
    def flatten(partition_list):
        return [item for sublist in partition_list for item in sublist]
