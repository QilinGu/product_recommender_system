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

users_who_reviewed_product
    key = (int) product node ID
    value = set of (int) user IDs that reviewed the product

products_users_purchased
    key = (int) user node ID
    value = set of (int) product IDs that the user purchased

product_graph
    key = (int) product ID
    value = set of tuples ((int) co-purchased product, (float) edge weight)

user_graph
    key = (int) user ID
    value = defaultdict of (int) user ID --> (float) edge weight

"""
def parse_file(filename, create_user_graph=False):
    # the next two maps are temporarily used to store mappings from amazon 
    # string user and product IDs to integers
    amazonid_to_id = dict()
    user_to_id = dict()

    users_who_reviewed_product = defaultdict(set)
    products_users_purchased = defaultdict(set)
    product_graph = defaultdict(set)

    # fill this if we're creating the user-user graph
    user_graph = defaultdict(dict)

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
                """for user in current_product_users_who_reviewed:
                    products_users_purchased[user].add(current_product_id)
                    users_who_reviewed_product[current_product_id].add(user)
                for copurchased in current_product_copurchased:
                    product_graph[copurchased].add((current_product_id, 0))
                    product_graph[current_product_id].add((copurchased, 0))"""

                # if we're creating the user graph, calculate similarity for each pair of users
                if create_user_graph:
                    for user1 in current_product_users_who_reviewed:
                        for user2 in current_product_users_who_reviewed:
                            if user1 == user2:
                                continue
                            dif = abs(ratings[user1] - ratings[user2])
                            user_graph[user1][user2] = user_graph[user1].get(user2, 0) + (1 if dif < 2 else -1)

                # reset the current product information
                current_product_copurchased = list()
                current_product_users_who_reviewed = list()
                current_product_id = None
                current_product_amazon_id = None
                ratings = dict()
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

                if create_user_graph:
                    if line[3] == RATING:
                        # Store this user's rating for the product
                        ratings[user_to_id[reviewer]] = int(line[4])
                    else:
                        print 'Error reading rating for product'

    # Remove edges with weight <= 0
    toRemove = defaultdict(set)
    removedCount = 0
    remainingEdgeCount = 0
    if create_user_graph:
        for user, edges in user_graph.iteritems():
            for similar_user, similarity_score in edges.iteritems():
                if similarity_score <= 0:
                    toRemove[user].add(similar_user)
                    removedCount += 1
                else:
                    remainingEdgeCount += 1
        print 'Edges removed:', removedCount
        print 'Edges remaining:', remainingEdgeCount
        for user in toRemove:
            for unsimilar_user in toRemove[user]:
                user_graph[user].pop(unsimilar_user)

    return users_who_reviewed_product, products_users_purchased, product_graph, user_graph


"""
creates the test set by choosing number_test_purchases to isolate. we store
pairs of userID->productID and remove those pairs from the
users_who_reviewed_product and products_users_purchased graphs
"""
number_test_purchases = 1000
def extract_test_set(user_purchases, product_reviewers, baseline, user_graph):
    test_set = set()
    while len(test_set) < number_test_purchases:
        random_user = random.randint(1, len(user_purchases))
        purchased_products = user_purchases[random_user]
        if len(purchased_products) < 2 or (not baseline and len(user_graph[random_user]) == 0):
            # if the user didn't purchase any items, move to the next one
            # if we're relying on the user graph (i.e. not using the baseline method) and
            # the user doesn't have any similar users, continue
            continue
        random_product = random.sample(purchased_products, 1)[0]
        test_set.add((random_user, random_product))
        user_purchases.get(random_user).discard(random_product)
        product_reviewers.get(random_product).discard(random_user)

    return test_set, user_purchases, product_reviewers


# get the score for a product to co-purchased product relationship
def get_score_baseline(product, copurchased_product, product_reviewers, user_purchases):
    edge_sum = 0
    for reviewer in product_reviewers[product]:
        if reviewer in product_reviewers[copurchased_product]:
            edge_sum += 1.0 / float(len(user_purchases[reviewer]))

    return edge_sum


# weight the product_graph using the formula from the Zhou paper
def weight_graph(product_graph, user_purchases, product_reviewers):
    for product, edges in product_graph.iteritems():
        new_edges = set()
        for edge in edges:
            copurchased_product = edge[0]
            o_j = len(product_reviewers[copurchased_product])
            if o_j == 0:
                weight = 0
            else:
                score = get_score_baseline(product, copurchased_product, product_reviewers, user_purchases)
                weight = float(score) / float(o_j)
            new_edges.add((copurchased_product, weight))
        product_graph[product] = new_edges

    return product_graph


# get recommended products for a particular user
number_predictions = 10
def make_baseline_prediction(user, user_purchases, product_graph):
    candidates = list()
    for product in user_purchases[user]:
        candidates += list(product_graph[product])
    candidates = [pair[0] for pair in sorted(candidates, reverse=True, key=lambda pair: pair[1])]
    
    return candidates[:number_predictions]


# calculate the accuracy of baseline predictions using just the product graph
def baseline_predictions(test_set, user_purchases, product_reviewers, product_graph):
    number_correct = 0
    for test_user, test_product in test_set:
        predictions = make_baseline_prediction(test_user, user_purchases, product_graph)
        if test_product in predictions:
            number_correct += 1

    print "number_correct: ", number_correct
    print "percentage correct: ", 100.0 * number_correct / float(len(test_set)), "%"


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
SIMILAR_USERS_THRESHOLD = number_predictions * 10

def get_products_from_product_graph(test_user, user_purchases, product_graph):
    c = set()
    for purchase in user_purchases[test_user]:
        for copurchased, _ in product_graph[purchase]:
            c.add(copurchased)
    if len(c) == 0:
        print 'No candidates for user', test_user
        #print user_purchases[test_user]
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

def load_product_graph_snap(product_graph):
    G = snap.TUNGraph.New()
    for product, copurchased_set in product_graph.iteritems():
        if not G.IsNode(product):
            G.AddNode(product)
        for copurchased, _ in copurchased_set:
            if not G.IsNode(copurchased):
                G.AddNode(copurchased)
            # To make sure we aren't adding duplicates
            if not G.IsEdge(product, copurchased):
                G.AddEdge(product, copurchased)
    return G

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

    return [pair[0] for pair in sorted(scored_candidates, reverse=True, key=lambda pair: pair[1])][:number_predictions]

# calculate the accuracy of baseline predictions using just the product graph
def our_predictions(test_set, user_purchases, product_graph, user_graph, candidates_from_product_graph):
    G = load_product_graph_snap(product_graph)
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
            predictions = score_candidates(c, s, G, candidates_from_product_graph)
        else:
            c = get_products_from_user_graph(test_user, user_purchases, user_graph)
            s = get_products_from_product_graph(test_user, user_purchases, product_graph)
            predictions = score_candidates(c, s, G, candidates_from_product_graph)

        print 'Number of candidates:', len(c)
        print 'Size of similarity set', len(s)

        if test_product in predictions:
            number_correct += 1

        progress += 1

    print "number_correct: ", number_correct
    print "percentage correct: ", 100.0 * number_correct / float(len(test_set)), "%"


baseline = False
alg_1 = False

def main():
    argv = sys.argv
    filename = argv[1]
    users_who_reviewed_product, products_users_purchased, product_graph, user_graph = parse_file(filename, not baseline)
    test_set, products_users_purchased, users_who_reviewed_product = extract_test_set(products_users_purchased, users_who_reviewed_product, baseline, user_graph)
    product_graph = weight_graph(product_graph, products_users_purchased, users_who_reviewed_product)

    if baseline:
        baseline_predictions(test_set, products_users_purchased, users_who_reviewed_product, product_graph)
    else:
        print 'Nodes in purchases graph:', len(products_users_purchased)
        print 'Nodes in user graph:', len(user_graph)
        our_predictions(test_set, products_users_purchased, product_graph, user_graph, alg_1)


if __name__ == '__main__':
    main()