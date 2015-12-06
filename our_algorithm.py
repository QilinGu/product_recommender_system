#!/usr/bin/python

from collections import defaultdict
import random
import sys
import snap

# identifiers for the lines in the file
ASIN = "ASIN:";
SIMILAR = "similar:";
RATING = "rating:";


""" 
create the various graphs from the file

products_users_purchased
    key = (int) user node ID
    value = set of (int) product IDs that the user purchased

product_graph
    key = (int) product ID
    value = set of tuples ((int) co-purchased product, (float) edge weight)

"""
def parse_file(filename):
    # the next two maps are temporarily used to store mappings from amazon 
    # string user and product IDs to integers
    amazonid_to_id = dict()
    user_to_id = dict()

    products_users_purchased = defaultdict(set)

    # user graph
    G_users = snap.TNEANet.New()
    # product graph
    G_products = snap.TUNGraph.New()

    products_processed = 0
    next_user_id = 1
    next_product_id = 1

    # info for the current product in the data file
    current_product_copurchased = list()
    current_product_users_who_reviewed = list()
    current_product_id = None
    current_product_amazon_id = None
    ratings = dict() # each user's rating for the current product

    with open(filename, 'r') as data_file:
        for line in data_file:
            line = line.strip(' ').split()
            if not line and current_product_amazon_id:
                # on empty line, store the current product info in the graphs
                products_processed += 1
                print products_processed
                """if (products_processed % 100 == 0):
                    print products_processed
                    print 'User graph:', G_users.GetNodes()"""
                for user in current_product_users_who_reviewed:
                    products_users_purchased[user].add(current_product_id)

                # make sure we have a node for the current product
                if not G_products.IsNode(current_product_id):
                    G_products.AddNode(current_product_id)
                # store copurchased products in snap graph
                for copurchased in current_product_copurchased:
                    # make sure we have a node for the copurchased product
                    if not G_products.IsNode(copurchased):
                        G_products.AddNode(copurchased)
                    
                    G_products.AddEdge(copurchased, current_product_id)

                # calculate similarity for each pair of users and store in snap graph
                for user1 in current_product_users_who_reviewed:
                    for user2 in current_product_users_who_reviewed:
                        if user1 == user2:
                            continue
                        # Add both users to the graph, if not already present
                        if not G_users.IsNode(user1):
                            G_users.AddNode(user1)
                        if not G_users.IsNode(user2):
                            G_users.AddNode(user2)                            

                        # Add edge if not already present 
                        # (only in one direction, because we iterate over all pairs)
                        if not G_users.IsEdge(user1, user2):
                            G_users.AddEdge(user1, user2)

                # reset the current product information
                current_product_copurchased = list()
                current_product_users_who_reviewed = list()
                current_product_id = None
                current_product_amazon_id = None
                ratings = dict()
                continue

            if not line:
                continue

            elif line[0] == ASIN:
                # this identifier means we've started a new product in the file
                current_product_amazon_id = line[1]
                if amazonid_to_id.get(current_product_amazon_id, None):
                    current_product_id = amazonid_to_id[current_product_amazon_id]
                else:
                    amazonid_to_id[current_product_amazon_id] = next_product_id
                    current_product_id = next_product_id
                    next_product_id += 1

            elif line[0] == SIMILAR and line[1] > 0:
                # store copurchased products
                copurchased_products = line[2:]
                for product in copurchased_products:
                    if amazonid_to_id.get(product, None):
                        current_product_copurchased.append(amazonid_to_id[product])
                    else:
                        amazonid_to_id[product] = next_product_id
                        current_product_copurchased.append(next_product_id)
                        next_product_id += 1

            elif line[0].startswith('1') or line[0].startswith('2'):
                # stores reviewed products
                reviewer = line[2]
                if user_to_id.get(reviewer, None):
                    current_product_users_who_reviewed.append(user_to_id[reviewer])
                else:
                    user_to_id[reviewer] = next_user_id
                    current_product_users_who_reviewed.append(next_user_id)
                    next_user_id += 1

                if line[3] == RATING:
                    # Store this user's rating for the product
                    ratings[user_to_id[reviewer]] = int(line[4])
                else:
                    print 'Error reading rating for product'

    print 'Number of products:', (next_product_id-1)
    print 'Number of users:', (next_user_id-1)

    return products_users_purchased, G_products, G_users

def add_edge_weights(filename, G_users):
    # the next two maps are temporarily used to store mappings from amazon 
    # string user and product IDs to integers
    amazonid_to_id = dict()
    user_to_id = dict()

    # add edge attribute
    G_users.AddFltAttrE("weight")

    products_processed = 0
    next_user_id = 1
    next_product_id = 1

    # info for the current product in the data file
    current_product_copurchased = list()
    current_product_users_who_reviewed = list()
    current_product_id = None
    current_product_amazon_id = None
    ratings = dict() # each user's rating for the current product

    with open(filename, 'r') as data_file:
        for line in data_file:
            line = line.strip(' ').split()
            if not line and current_product_amazon_id:
                # on empty line, store the current product info in the graphs
                products_processed += 1
                if (products_processed % 1000 == 0):
                    print products_processed
                    print 'User graph:', G.GetNodes()

                # calculate similarity for each pair of users and store in snap graph
                for i in xrange(0, len(current_product_users_who_reviewed)):
                    for j in xrange(i+1, len(current_product_users_who_reviewed)):
                        user1 = current_product_users_who_reviewed[i]
                        user2 = current_product_users_who_reviewed[j]

                        # Get edges and edge weights
                        edge1 = G_users.GetEI(user1, user2)
                        weightVec1 = G_users.FltAttrValueEI(edge1)
                        edge2 = G_users.GetEI(user2, user1)
                        weightVec2 = G_users.FltAttrValueEI(edge2)

                        dif = abs(ratings[user1] - ratings[user2])
                        increment = 1 if dif < 2 else -1

                        # Haven't assigned a weight yet
                        if weightVec1.Len() == 0 and weightVec2.Len() == 0:
                            G_users.AddFltAttrDatE(edge1, increment, "weight")
                            G_users.AddFltAttrDatE(edge2, increment, "weight")
                        # Weights are set and equal, which means they're valid
                        elif weightVec1[0] == weightVec2[0]:
                            G_users.AddFltAttrDatE(edge1, weightVec1[0] + increment, "weight")
                            G_users.AddFltAttrDatE(edge2, weightVec1[0] + increment, "weight")
                        # Something wrong
                        else:
                            print 'Something wrong with graph'

                # reset the current product information
                current_product_copurchased = list()
                current_product_users_who_reviewed = list()
                current_product_id = None
                current_product_amazon_id = None
                ratings = dict()
                continue

            if not line:
                continue

            elif line[0] == ASIN:
                # this identifier means we've started a new product in the file
                current_product_amazon_id = line[1]
                if amazonid_to_id.get(current_product_amazon_id, None):
                    current_product_id = amazonid_to_id[current_product_amazon_id]
                else:
                    amazonid_to_id[current_product_amazon_id] = next_product_id
                    current_product_id = next_product_id
                    next_product_id += 1

            elif line[0] == SIMILAR and line[1] > 0:
                # store copurchased products
                copurchased_products = line[2:]
                for product in copurchased_products:
                    if amazonid_to_id.get(product, None):
                        current_product_copurchased.append(amazonid_to_id[product])
                    else:
                        amazonid_to_id[product] = next_product_id
                        current_product_copurchased.append(next_product_id)
                        next_product_id += 1

            elif line[0].startswith('1') or line[0].startswith('2'):
                # stores reviewed products
                reviewer = line[2]
                if user_to_id.get(reviewer, None):
                    current_product_users_who_reviewed.append(user_to_id[reviewer])
                else:
                    user_to_id[reviewer] = next_user_id
                    current_product_users_who_reviewed.append(next_user_id)
                    next_user_id += 1

                if line[3] == RATING:
                    # Store this user's rating for the product
                    ratings[user_to_id[reviewer]] = int(line[4])
                else:
                    print 'Error reading rating for product'

# Remove edges with weight <= 0
def remove_negative_edges(user_graph):
    removedCount = 0

    nodeIter = user_graph.BegNI()
    while True:
        if nodeIter == user_graph.EndNI():
            break
        toRemove = set()
        # figure out which edges to remove (weight < 0)
        for index in xrange(0, nodeIter.GetOutDeg()):
            otherNodeId = nodeIter.GetOutNId(index)
            edge = user_graph.GetEdge(nodeIter.GetId(), otherNodeId)
            # store this as something to remove
            if user_graph.GetFltAttrDatE(edge, "weight") <= 0:
                toRemove.add((nodeIter.GetId(), otherNodeId))
        for edge in toRemove:
            user_graph.DelEdge(edge[0], edge[1])
            removedCount += 1
        toRemove.clear()
        nodeIter = nodeIter.Next()

    print 'Edges removed:', removedCount
    print 'Edges remaining:', user_graph.GetEdges()

"""
creates the test set by choosing number_test_purchases to isolate. we store
pairs of userID->productID and remove those pairs from the products_users_purchased graphs
"""
number_test_purchases = 1000
def extract_test_set(user_purchases, user_graph):
    test_set = set()
    while len(test_set) < number_test_purchases:
        random_user = random.randint(1, len(user_purchases))
        purchased_products = user_purchases[random_user]

        # skip if the user didn't purchase any items or doesn't have any similar users
        if len(purchased_products) < 2:
            if user_graph.getNI(random_user).GetOutDeg() == 0:
                continue

        random_product = random.sample(purchased_products, 1)[0]
        test_set.add((random_user, random_product))
        user_purchases.get(random_user).discard(random_product)

    return test_set, user_purchases

"""
Algorithm #1: Candidates are one hop away from something you've purchased, scored based on distance
from what similar users purchased
    - Create user-user graph, where edge weights represent strength of similarity between users
    - To generate recommendations for user u:
        - Candidate set C = items that are commonly co-purchased with items that u purchased
        - Similarity set S = (item, sim_score) for items purchased by x users most similar to u (but not purchased by u)
        - Select top n items from C based on shortest path to an item in S (weighted by similarity with that user?)

Algorithm #2: Candidates are items purchased by similar users, scored based on distance from what you purchased
    - Create user-user graph, where edge weights represent strength of similarity between users
    - To generate recommendations for user u:
        - Candidate set C = (item, sim_score) for items that were purchased by x users most similar to u 
                            (but not purchased by u)
        - Similarity set S = items that u has purchased
        - Select top n items from C based on shortest path to an item in S 
            (weighted by similarity with the user who bought the item?)
"""

USER_SIM_SCORE_WEIGHT = 0.5
DISTANCE_ZERO_SCORE = 0.5
SHOULD_LIMIT_SIMILAR_USERS = True
NUMBER_PREDICTIONS = 10
SIMILAR_USERS_THRESHOLD = NUMBER_PREDICTIONS * 10

# Get all products that are neighbours of the products the test user has purchased
def get_products_from_product_graph(test_user, user_purchases, product_graph):
    c = set()
    for purchase in user_purchases[test_user]:
        node = product_graph.GetNI(purchase)
        for index in xrange(0, node.GetOutDeg()):
            otherNodeId = node.GetOutNId(index)
            c.add(otherNodeId)

    if len(c) == 0:
        print 'No candidates for user', test_user
    return c

def get_products_from_user_graph(test_user, user_purchases, user_graph):
    s = set()
    #print 'Number of similar users:', len(user_graph[test_user])

    similar_users = sorted([(k,v) for k, v in user_graph[test_user].iteritems()], reverse=True, key=lambda pair: pair[1])
    if SHOULD_LIMIT_SIMILAR_USERS:
        similar_users = similar_users[:SIMILAR_USERS_THRESHOLD]
    #print 'Limited number of similar users', len(similar_users)

    for similar_user, weight in similar_users:
        for purchase in user_purchases[similar_user]:
            if purchase not in user_purchases[test_user]:
                s.add((purchase, weight))
    return s

# Find the highest value of sim_score / distance for any product in s
def algorithm1_score(candidate, s, G):
    if len(s) == 0:
        return 0

    """for product, user_sim_score in s:
        print 'Similarity score:', user_sim_score
        print 'Candidate score:', USER_SIM_SCORE_WEIGHT * user_sim_score / max(float(snap.GetShortPath(G, candidate, product)), DISTANCE_ZERO_SCORE)"""

    return max([USER_SIM_SCORE_WEIGHT * user_sim_score / max(float(snap.GetShortPath(G, candidate, product)), DISTANCE_ZERO_SCORE) for product, user_sim_score in s])

def algorithm2_score(candidate, sim_score, s, G):
    if not G.IsNode(candidate) or len(s) == 0:
        return 0
    shortestPath = max([snap.GetShortPath(G, candidate, purchased_product) for purchased_product in s])
    return USER_SIM_SCORE_WEIGHT * sim_score / max(float(shortestPath), DISTANCE_ZERO_SCORE)

# Score each of the candidates, return the top number_predictions predictions
def score_candidates(c, s, G, candidates_from_product_graph):
    scored_candidates = None

    if candidates_from_product_graph:
        scored_candidates = [(candidate, algorithm1_score(candidate, s, G)) for candidate in c]
    else:
        scored_candidates = [(candidate, algorithm2_score(candidate, sim_score, s, G)) for candidate, sim_score in c]

    return [pair[0] for pair in sorted(scored_candidates, reverse=True, key=lambda pair: pair[1])][:NUMBER_PREDICTIONS]

# calculate the accuracy of baseline predictions using just the product graph
def our_predictions(test_set, user_purchases, product_graph, user_graph, candidates_from_product_graph):
    number_correct = 0
    in_candidate_set = 0
    progress = 0
    for test_user, test_product in test_set:
        if progress > 0 and progress % 50 == 0: # So we know how far we are
            print '\nPredictions made:', progress, '\n'

        c = None
        s = None
        predictions = None

        if candidates_from_product_graph:
            c = get_products_from_product_graph(test_user, user_purchases, product_graph)
            s = get_products_from_user_graph(test_user, user_purchases, user_graph)
            predictions = score_candidates(c, s, product_graph, candidates_from_product_graph)
        else:
            c = get_products_from_user_graph(test_user, user_purchases, user_graph)
            s = get_products_from_product_graph(test_user, user_purchases, product_graph)
            predictions = score_candidates(c, s, product_graph, candidates_from_product_graph)

        print 'Number of candidates:', len(c)
        print 'Size of similarity set', len(s)

        if test_product in predictions:
            number_correct += 1

        progress += 1

    print "number_correct: ", number_correct
    print "percentage correct: ", 100.0 * number_correct / float(len(test_set)), "%"


alg_1 = False

def main():
    argv = sys.argv
    filename = argv[1]
    products_users_purchased, product_graph, user_graph = parse_file(filename)
    add_edge_weights(filename, user_graph)
    remove_negative_edges(user_graph)
    test_set, products_users_purchased = extract_test_set(products_users_purchased, user_graph)

    print 'Nodes in purchases graph:', len(products_users_purchased)
    print 'Nodes in user graph:', len(user_graph)
    our_predictions(test_set, products_users_purchased, product_graph, user_graph, alg_1)


if __name__ == '__main__':
    main()