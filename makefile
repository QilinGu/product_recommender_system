parse_data: parse_data.cpp
	g++ -g -O0 -std=c++11 parse_data.cpp -o parse_data

clean:
	rm -f parse_data