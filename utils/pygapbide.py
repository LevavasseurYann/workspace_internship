class GapbideManager:
    """
    Manager d'une instance :class:Gabide

    Variables d'Instance:
        * gp: Gapbide
            Instance de l'algo a manager
        * dataset: Array[int]
            Liste des donnees sax les entiers font office de symboles
        * res: Array[[int: X*], int: Y, Z(int: Z1, int: Z2, int: Z3)]
            * X* Pattern d'entiers ex: 244695
            * Y Support du pattern
            * Z( * Z1: Position du patterns, indice de la transaction
                 * Z2: Indice au sein de la transaction du debut du patterns
                 * Z3: Indice de fin...)
    """
    def __init__(self, gp = None):
        self.gp = gp
        self.dataset = None
        self.res = None

    def run(self):
        self.res = self.gp.run()

    def clean_import_db(self, db):
        for compact_list in db:
            self.dataset.append(compact_list.ravel())

    def reset_gp(self, sup, m, n):
        self.gp = Gapbide(self.dataset, sup, m, n)

class Gapbide:
    def __init__(self, sdb, sup, m, n):
        '''
        sdb: alist of sequences,
        sup: the minimum threshold of support,
        m,n: the gap [m,n]
        '''
        self.sdb = sdb
        self.sup = sup
        self.m = m
        self.n = n
        self.count_closed = 0
        self.count_non_closed = 0
        self.count_pruned = 0

    def run(self):
        l1_patterns = self.gen_l1_patterns()
        for pattern, sup, pdb in l1_patterns:
            self.span(pattern, sup, pdb)

    def output(self, pattern, sup, pdb):
        '''
        overide this function to output patterns to files.
        '''
        print(pattern, sup, pdb)
        return [pattern, sup, pdb]

    def gen_l1_patterns(self):
        '''
        generate length-1 patterns
        '''
        pdb_dict = dict()
        for sid in range(len(self.sdb)):
            seq = self.sdb[sid]
            for pos in range(len(seq)):
                if seq[pos] in pdb_dict:
                    pdb_dict[seq[pos]].append((sid, pos, pos))
                else:
                    pdb_dict[seq[pos]] = [(sid, pos, pos)]
        patterns = []
        for item, pdb in pdb_dict.items():
            sup = len(set([i[0] for i in pdb]))
            if sup >= self.sup:
                patterns.append(([item], sup, pdb))
        return patterns

    def span(self, pattern, sup, pdb):
        (backward, prune) = self.backward_check(pattern, sup, pdb)
        if prune:
            self.count_pruned += 1
            return
        forward = self.forward_check(pattern, sup, pdb)
        if not(backward or forward):
            self.count_closed += 1
            self.output(pattern, sup, pdb)
        else:
            self.count_non_closed += 1
        pdb_dict = dict()
        for (sid, begin, end) in pdb:
            seq = self.sdb[sid]
            new_begin = end + 1 + self.m
            new_end = end + 2 + self.n
            if new_begin >= len(seq):
                continue
            if new_end > len(seq):
                new_end = len(seq)
            for pos in range(new_begin, new_end):
                if seq[pos] in pdb_dict:
                    pdb_dict[seq[pos]].append((sid, begin, pos))
                else:
                    pdb_dict[seq[pos]] = [(sid, begin, pos)]
        for item, new_pdb in pdb_dict.items():
            sup = len(set([i[0] for i in new_pdb]))
            if sup >= self.sup:
                # add new pattern
                new_pattern = pattern[:]
                new_pattern.append(item)
                self.span(new_pattern, sup, new_pdb)

    def forward_check(self, pattern, sup, pdb):
        sids = {}
        forward = False
        for (sid, begin, end) in pdb:
            seq = self.sdb[sid]
            new_begin = end + 1 + self.m
            new_end = end + 2 + self.n
            if new_begin >= len(seq):
                continue
            if new_end > len(seq):
                new_end = len(seq)
            for pos in range(new_begin, new_end):
                if seq[pos] in sids:
                    sids[seq[pos]].append(sid)
                else:
                    sids[seq[pos]] = [sid]
        for item, sidlist in sids.items():
            seq_sup = len(set(sidlist))
            if seq_sup == sup:
                forward = True
                break
        return forward

    def backward_check(self, pattern, sup, pdb):
        sids = {}
        backward = False
        prune = False
        for (sid, begin, end) in pdb:
            seq = self.sdb[sid]
            new_begin = begin - self.n - 1
            new_end = begin - self.m
            if new_end < 0:
                continue
            if new_begin < 0:
                new_begin = 0
            for pos in range(new_begin, new_end):
                if seq[pos] in sids:
                    sids[seq[pos]].append(sid)
                else:
                    sids[seq[pos]] = [sid]
        for item, sidlist in sids.items():
            seq_sup = len(set(sidlist))
            uni_sup = len(sidlist)
            if uni_sup == len(pdb):
                prune = True
            if seq_sup == sup:
                backward = True
            if backward and prune:
                break
        return (backward, prune)
