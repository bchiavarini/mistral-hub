from restapi.utilities.logs import log
import dballe
import os
import itertools
import subprocess
import glob


user = os.environ.get("ALCHEMY_USER")
pw = os.environ.get("ALCHEMY_PASSWORD")
host = os.environ.get("ALCHEMY_HOST")
engine = os.environ.get("ALCHEMY_DBTYPE")
port = os.environ.get("ALCHEMY_PORT")

DB = dballe.DB.connect("{engine}://{user}:{pw}@{host}:{port}/DBALLE".format(engine=engine, user=user, pw=pw,
                                                                            host=host, port=port))

class BeDballe():

    @staticmethod
    def build_explorer():
        explorer = dballe.Explorer()
        with explorer.rebuild() as update:
            with DB.transaction() as tr:
                update.add_db(tr)
        return explorer

    @staticmethod
    def load_filters(params,q=None):
        # create and update the explorer object
        explorer = BeDballe.build_explorer()

        # parse the query
        query = BeDballe.from_query_to_dic(q)
        log.info('query: {}'.format(query))

        # check if requested networks are in that dataset
        query_networks_list = []
        if 'network' in query:
            if not all(elem in params for elem in query['network']):
                return None
            else:
                query_networks_list = query['network']
        else:
            # if there aren't requested network, data will be filtered only by dataset
            query_networks_list = params
        log.debug('query networks list : {}'.format(query_networks_list))

        # perform the queries in database to get the list of possible filters
        fields = {}
        networks_list = []
        variables = []
        levels = []
        tranges = []
        for n in query_networks_list:
            # filter the dballe database by network
            explorer.set_filter({'report': n})

            # list of the variables of this network
            net_variables = []

            ######### VARIABLES FIELDS
            # get the list of all the variables of the network
            varlist = explorer.varcodes

            #### PRODUCT is in the query filters
            if 'product' in query:
                # check if the requested variables are in the network
                for e in query['product']:
                    if e in varlist:
                        # if there is append it to the temporary list of matching variables
                        net_variables.append(e)
                if not net_variables:
                    # if at the end of the cycle the temporary list of matching variables is still empty go to the next network
                    continue
            else:
                # if product is not in the query filter append all the variable of the network o the final list of the fields
                net_variables = varlist

            ######### LEVELS FIELDS
            level_fields, net_variables_temp = BeDballe.get_fields(explorer, n, net_variables, query, param='level')
            if not level_fields:
                continue
            # check if the temporary list of variable is not more little of the general one. If it is, replace the general list
            if not all(elem in net_variables_temp for elem in net_variables):
                net_variables = net_variables_temp

            ######### TIMERANGES FIELDS
            trange_fields, net_variables_temp, level_fields_temp = BeDballe.get_fields(explorer, n, net_variables, query, param='timerange')
            if not trange_fields:
                continue
            # check if the temporary list of variable is not more little of the general one. If it is, replace the general list
            if not all(elem in net_variables_temp for elem in net_variables):
                net_variables = net_variables_temp

            # check if the temporary list of levels is not more little of the general one. If it is, replace the general list
            if not all(elem in level_fields_temp for elem in level_fields):
                level_fields = level_fields_temp

            # append in the final list the timeranges retrieved
            tranges.extend(x for x in trange_fields if x not in tranges)

            # append in the final list the levels retrieved
            levels.extend(x for x in level_fields if x not in levels)

            # append all the network variables in the final field list
            variables.extend(x for x in net_variables if x not in variables)

            # if there are results, this network can be in the final fields
            networks_list.append(n)

        # if matching fields were found network list can't be empty
        if networks_list:
            # create the final dictionary
            fields['network'] = BeDballe.from_list_of_params_to_list_of_dic(networks_list)
            fields['product'] = BeDballe.from_list_of_params_to_list_of_dic(variables)
            fields['level'] = BeDballe.from_list_of_params_to_list_of_dic(levels)
            fields['timerange'] = BeDballe.from_list_of_params_to_list_of_dic(tranges)

            # add description in model for the levels and the timeranges?
            return fields
        else:
            return None

        # TODO: il reftime a che mi serve in questo caso??

    @staticmethod
    def get_fields(explorer, network, variables,query,param):
        # filter the dballe database by list of variables (level and timerange depend on variable)
        explorer.set_filter({'varlist': variables,'report': network})
        level_list = []
        # get the list of all the fields for requested param according to the variables
        if param == 'level':
            param_list = explorer.levels
        elif param == 'timerange':
            param_list = explorer.tranges
            # if the param is timerange, 3 values packed are needed
            level_list = explorer.levels

        # parse the dballe object
        param_list_parsed = []
        for e in param_list:
            if param == 'level':
                p = BeDballe.from_level_object_to_string(e)
            elif param == 'timerange':
                p = BeDballe.from_trange_object_to_string(e)
            param_list_parsed.append(p)

        if level_list:
            level_list_parsed = []
            # parse the level list
            for l in level_list:
                level = BeDballe.from_level_object_to_string(l)
                level_list_parsed.append(level)

        #### the param is in the query filters
        if param in query:
            temp_fields = []
            # check if the requested params matches the one required for the given variables
            for e in query[param]:
                if e in param_list_parsed:
                    # if there is append it to the temporary list of matching fields
                    temp_fields.append(e)
            if not temp_fields:
                # if at the end of the cycle the temporary list of matching variables is still empty go to the next network
                if param == 'level':
                    return None, None
                elif param == 'timerange':
                    return None, None, None
            else:
                # if only the param is in query and not product, discard from the network variable list all products not matching the param
                if 'product' not in query:
                    variables_by_param = []
                    levels_by_trange = []
                    for qp in query[param]:
                        # for each variable i check if the param matches
                        for v in variables:
                            explorer.set_filter({'var': v})
                            if param == 'level':
                                param_list = explorer.levels
                            elif param == 'timerange':
                                param_list = explorer.tranges
                            # parse the dballe object
                            param_list_parsed = []
                            for e in param_list:
                                if param == 'level':
                                    p = BeDballe.from_level_object_to_string(e)
                                elif param == 'timerange':
                                    p = BeDballe.from_trange_object_to_string(e)
                                param_list_parsed.append(p)
                            # if the param matches append the variable in a temporary list
                            if qp in param_list_parsed:
                                variables_by_param.append(v)
                    # the temporary list of variables matching the requested param become the list of the variable of the network
                    variables = variables_by_param
                    # if the list of variables has been modified, we are filtering by timeranges and level is not in
                    # query, i have to check if the level fields still matches the new variable list
                    if param == 'timerange' and 'level' not in query:
                        # for each variable check if the level matches
                        for level in level_list_parsed:
                            for v in variables:
                                explorer.set_filter({'var': v})
                                var_level = explorer.levels
                                var_level_parsed = []
                                # parse the dballe.Level object
                                for e in var_level:
                                    l = BeDballe.from_level_object_to_string(e)
                                    var_level_parsed.append(l)
                                # if the level matches append the level in a temporary list
                                if level in var_level_parsed:
                                    levels_by_trange.append(level)
                        # the temporary list of levels matching the resulted variables become the list of levels to return
                        level_list_parsed = levels_by_trange
                if param == 'level':
                    return temp_fields, variables
                elif param == 'timerange':
                    return temp_fields, variables, level_list_parsed
        else:
            # if param is not in the query filter append return all the fields
            if param == 'level':
                return param_list_parsed, variables
            elif param == 'timerange':
                return param_list_parsed, variables, level_list_parsed

    @staticmethod
    def from_query_to_dic(q):
        # example of query string: string= "reftime: >=2020-02-01 01:00,<=2020-02-04 15:13;level:1,0,0,0 or 103,2000,0,0;product:B11001 or B13011;timerange:0,0,3600 or 1,0,900;network:fidupo or agrmet"
        params_list = ['reftime', 'network', 'product', 'level', 'timerange']
        query_list = q.split(';')
        query_dic = {}
        for e in query_list:
            for p in params_list:
                if e.startswith(p):
                    val = e.split(p + ':')[1]
                    # ex. from 'level:1,0,0,0 or 103,2000,0,0' to '1,0,0,0 or 103,2000,0,0'

                    # reftime param has to be parsed differently
                    if p == 'reftime':
                        refs = {}
                        reftimes = [x.strip() for x in val.split(',')]
                        # ex. from ' >=2020-02-01 01:00,<=2020-02-04 15:13' to ['>=2020-02-01 01:00', '<=2020-02-04 15:13']
                        for r in reftimes:
                            if r.startswith('>'):
                                refs['min_reftime'] = r.strip('>=')
                            if r.startswith('<'):
                                refs['max_reftime'] = r.strip('<=')
                            if r.startswith('='):
                                refs['min_reftime'] = refs['max_reftime'] = r.strip('=')
                        query_dic['reftime'] = refs

                    # parsing all other parameters
                    else:
                        val_list = [x.strip() for x in val.split('or')]
                        query_dic[p] = val_list
        return query_dic

    @staticmethod
    def from_level_object_to_string(level):
        level_list=[]

        if level.ltype1:
            ltype1 = str(level.ltype1)
        else:
            ltype1= '0'
        level_list.append(ltype1)

        if level.l1:
            l1 = str(level.l1)
        else:
            l1= '0'
        level_list.append(l1)

        if level.ltype2:
            ltype2 = str(level.ltype2)
        else:
            ltype2= '0'
        level_list.append(ltype2)

        if level.l2:
            l2 = str(level.l2)
        else:
            l2= '0'
        level_list.append(l2)

        level_parsed = ','.join(level_list)
        return level_parsed

    @staticmethod
    def from_trange_object_to_string(trange):
        trange_list = []

        pind = str(trange.pind)
        trange_list.append(pind)

        p1 = str(trange.p1)
        trange_list.append(p1)

        p2 = str(trange.p2)
        trange_list.append(p2)

        trange_parsed = ','.join(trange_list)
        return trange_parsed

    @staticmethod
    def from_list_of_params_to_list_of_dic(param_list):
        list_dic = []
        for p in param_list:
            item = {}
            item['dballe_p'] = p
            list_dic.append(item)
        return list_dic

    @staticmethod
    def from_filters_to_lists(filters):
        fields = []
        queries = []
        allowed_keys = ['level', 'network', 'product', 'timerange']
        dballe_keys = ['level', 'rep_memo', 'var', 'trange']

        for key, value in filters.items():
            if key in allowed_keys:
                # change the key name from model to dballe name
                key_index = allowed_keys.index(key)
                fields.append(dballe_keys[key_index])

                field_queries = []
                for e in value:
                    if key == 'timerange' or key == 'level':
                        # transform the timerange or level value in a tuple (required for dballe query)
                        tuple_list = []
                        for v in e['dballe_p'].split(','):
                            if key == 'level' and v == '0':
                                val = None
                                tuple_list.append(val)
                            else:
                                tuple_list.append(int(v))
                        field_queries.append(tuple(tuple_list))
                    else:
                        field_queries.append(e['dballe_p'])
                queries.append(field_queries)
            else:
                continue

        return fields, queries

    @staticmethod
    def extract_data(fields, queries, outfile):
        # get all the possible combinations of queries
        all_queries = list(itertools.product(*queries))
        counter = 1
        cat_cmd = ['cat']
        for q in all_queries:
            dballe_query = {}
            for k, v in zip(fields, q):
                dballe_query[k] = v
            #log.debug('counter= {} dballe query: {}'.format(str(counter), dballe_query))
            # check if the query gives a result:
            # create and update the explorer object
            explorer = BeDballe.build_explorer()
            # set the query as filter
            explorer.set_filter(dballe_query)
            # check if the query gives a result using any field
            level = explorer.levels
            if not level:
                continue

            # set the filename for the partial extraction
            filebase, fileext = os.path.splitext(outfile)
            part_outfile = filebase + '_part' + str(counter) + fileext + '.tmp'
            # extract in a partial extraction
            with DB.transaction() as tr:
                tr.export_to_file(dballe_query, 'BUFR', part_outfile)

            cat_cmd.append(part_outfile)
            # update counter
            counter += 1

        # join all the partial extractions
        with open(outfile, mode='w') as output:
            ext_proc = subprocess.Popen(cat_cmd, stdout=output)
            ext_proc.wait()
            if ext_proc.wait() != 0:
                raise Exception('Failure in post processing')